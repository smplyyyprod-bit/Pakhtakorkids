"""Drive real Telegram updates through the dispatcher with a mock transport.

This exercises the full request path - middleware, auth, role filters, handlers,
services, database - without contacting Telegram. Outgoing API calls are
captured instead of sent, so the assertions look at what the bot would actually
reply.

    python -m scripts.verify_handlers
"""

import asyncio
import sys
from datetime import datetime, timezone
from typing import Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.types import (
    CallbackQuery,
    Chat,
    Message,
    Update,
    User as TgUser,
)

from app.domain.models import Role
from app.infrastructure.database import SessionLocal
from app.infrastructure.services import UserService
from app.presentation.telegram.bot import create_dispatcher

ADMIN_ID = 100000001
MANAGER_ID = 100000002
STRANGER_ID = 999999999

passed = 0
failed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}  {detail}")


class RecordingSession(BaseSession):
    """Captures outgoing API calls instead of performing them."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def close(self) -> None:
        return None

    async def stream_content(self, *args, **kwargs):  # pragma: no cover
        yield b""

    async def make_request(
        self, bot: Bot, method: TelegramMethod, timeout: int | None = None
    ):
        name = type(method).__name__
        payload = method.model_dump(exclude_none=True)
        self.calls.append((name, payload))

        # Return the minimum each call site needs to keep going.
        if name == "SendMessage":
            return Message(
                message_id=len(self.calls),
                date=datetime.now(timezone.utc),
                chat=Chat(id=payload.get("chat_id", 1), type="private"),
                text=payload.get("text", ""),
            )
        if name in {"EditMessageText", "DeleteWebhook", "SetMyCommands"}:
            return True
        if name == "AnswerCallbackQuery":
            return True
        return True

    def texts(self) -> str:
        return "\n".join(
            str(p.get("text", "")) for _, p in self.calls if "text" in p
        )

    def button_labels(self) -> str:
        """Button captions live in reply_markup, not in the message text."""
        labels: list[str] = []
        for _, payload in self.calls:
            markup = payload.get("reply_markup")
            if not markup:
                continue
            rows = getattr(markup, "inline_keyboard", None)
            if rows is None and isinstance(markup, dict):
                rows = markup.get("inline_keyboard")
            for row in rows or []:
                for button in row:
                    text = getattr(button, "text", None)
                    if text is None and isinstance(button, dict):
                        text = button.get("text")
                    if text:
                        labels.append(str(text))
        return "\n".join(labels)

    def screen(self) -> str:
        """Everything the user would see: message text plus button captions."""
        return self.texts() + "\n" + self.button_labels()

    def methods(self) -> list[str]:
        return [name for name, _ in self.calls]

    def reset(self) -> None:
        self.calls.clear()


def make_message_update(update_id: int, user_id: int, text: str) -> Update:
    tg_user = TgUser(id=user_id, is_bot=False, first_name="Test")
    return Update(
        update_id=update_id,
        message=Message(
            message_id=update_id,
            date=datetime.now(timezone.utc),
            chat=Chat(id=user_id, type="private"),
            from_user=tg_user,
            text=text,
        ),
    )


def make_callback_update(update_id: int, user_id: int, data: str) -> Update:
    tg_user = TgUser(id=user_id, is_bot=False, first_name="Test")
    return Update(
        update_id=update_id,
        callback_query=CallbackQuery(
            id=str(update_id),
            from_user=tg_user,
            chat_instance="test",
            data=data,
            message=Message(
                message_id=update_id,
                date=datetime.now(timezone.utc),
                chat=Chat(id=user_id, type="private"),
                text="prev",
            ),
        ),
    )


async def ensure_users() -> None:
    """Make sure the two privileged accounts exist for this run."""
    async with SessionLocal() as session:
        service = UserService(session)
        await service.grant_access(
            telegram_id=ADMIN_ID, full_name="Админ Тестов", role=Role.ADMIN
        )
        await service.grant_access(
            telegram_id=MANAGER_ID, full_name="Менеджер Тестов", role=Role.MANAGER
        )


async def main() -> int:
    await ensure_users()

    session = RecordingSession()
    bot = Bot(token="111111111:AAtest_token_for_offline_verification_only", session=session)
    dp = create_dispatcher()

    uid = 1000

    async def feed(update: Update) -> RecordingSession:
        session.reset()
        await dp.feed_update(bot, update)
        return session

    print("\n[1] /start")
    uid += 1
    await feed(make_message_update(uid, ADMIN_ID, "/start"))
    admin_start = session.screen()
    check("admin /start replies", len(session.calls) > 0)
    check("admin sees administrator menu", "администратор" in admin_start.lower(), admin_start[:120])
    check(
        "admin menu offers report filling",
        "Отчёты за сегодня" in admin_start or "Отделения" in admin_start,
    )

    uid += 1
    await feed(make_message_update(uid, MANAGER_ID, "/start"))
    manager_start = session.screen()
    check("manager sees manager menu", "руководител" in manager_start.lower(), manager_start[:120])
    check("manager menu offers analytics", "Аналитика" in manager_start)

    print("\n[2] Access control")
    uid += 1
    await feed(make_message_update(uid, STRANGER_ID, "/start"))
    stranger = session.screen()
    check("unknown user is refused", "нет доступа" in stranger.lower(), stranger[:120])
    check(
        "unknown user gets no menu",
        "Аналитика" not in stranger and "Отделения" not in stranger,
    )

    print("\n[3] Role enforcement: admin must NOT reach analytics")
    for command in ("/dashboard", "/analytics", "/admin", "/export", "/coaches", "/monthly"):
        uid += 1
        await feed(make_message_update(uid, ADMIN_ID, command))
        text = session.screen()
        # No handler should match, so nothing is sent back at all.
        check(
            f"admin {command} produces no manager output",
            "Панель управления" not in text and "Рейтинг" not in text and "Администрирование" not in text,
            text[:100],
        )

    print("\n[4] Manager analytics commands work")
    uid += 1
    await feed(make_message_update(uid, MANAGER_ID, "/dashboard"))
    dash = session.texts()
    check("manager /dashboard renders", "Панель управления" in dash, dash[:120])
    check("dashboard shows coach count", "Всего тренеров" in dash)
    check("dashboard shows completion", "Процент" in dash)

    uid += 1
    await feed(make_message_update(uid, MANAGER_ID, "/analytics"))
    analytics = session.texts()
    check("manager /analytics renders", "Аналитика" in analytics, analytics[:120])

    uid += 1
    await feed(make_message_update(uid, MANAGER_ID, "/coaches"))
    coaches = session.texts()
    check("manager /coaches lists coaches", "Тренеры" in coaches, coaches[:120])

    uid += 1
    await feed(make_message_update(uid, MANAGER_ID, "/admin"))
    admin_panel = session.texts()
    check("manager /admin renders", "Администрирование" in admin_panel, admin_panel[:120])

    print("\n[5] Admin report commands work")
    uid += 1
    await feed(make_message_update(uid, ADMIN_ID, "/today"))
    today_text = session.texts()
    check("admin /today renders", "Отчёты за" in today_text, today_text[:120])

    uid += 1
    await feed(make_message_update(uid, ADMIN_ID, "/branches"))
    branches_text = session.texts()
    check("admin /branches renders", "отделение" in branches_text.lower(), branches_text[:120])
    check(
        "branch picker includes buttons",
        any("reply_markup" in p for _, p in session.calls),
    )

    print("\n[6] /help is role-aware")
    uid += 1
    await feed(make_message_update(uid, ADMIN_ID, "/help"))
    help_admin = session.texts()
    check("admin help mentions admin commands", "/branches" in help_admin)
    check("admin help hides analytics commands", "/dashboard" not in help_admin)

    uid += 1
    await feed(make_message_update(uid, MANAGER_ID, "/help"))
    help_manager = session.texts()
    check("manager help mentions analytics", "/dashboard" in help_manager)

    print("\n[7] /cancel")
    uid += 1
    await feed(make_message_update(uid, ADMIN_ID, "/cancel"))
    check("cancel responds", len(session.calls) > 0)

    print("\n[8] Inline keyboard callbacks")
    uid += 1
    await feed(make_callback_update(uid, MANAGER_ID, "adm:dashboard:0"))
    cb_dash = session.texts()
    check("dashboard button works", "Панель управления" in cb_dash, cb_dash[:120])
    check("callback is acknowledged", "AnswerCallbackQuery" in session.methods())

    uid += 1
    await feed(make_callback_update(uid, MANAGER_ID, "adm:analytics:0"))
    check("analytics button works", "Аналитика" in session.texts())

    uid += 1
    await feed(make_callback_update(uid, ADMIN_ID, "adm:dashboard:0"))
    check(
        "admin pressing a manager callback gets nothing",
        "Панель управления" not in session.texts(),
    )

    uid += 1
    await feed(make_callback_update(uid, ADMIN_ID, "nav:home"))
    check("home button returns admin menu", "администратор" in session.texts().lower())

    print("\n[9] Daily report flow (admin)")
    async with SessionLocal() as db:
        from app.infrastructure.services import BranchService

        branches = await BranchService(db).list_branches()
        branch_id = branches[0].id if branches else None

    if branch_id:
        uid += 1
        await feed(make_callback_update(uid, ADMIN_ID, f"br:pick:{branch_id}"))
        form = session.texts()
        check("selecting a branch opens a coach form", "Присутствие" in form, form[:150])
        check("form shows step progress", "шаг 1/7" in form, form[:150])

        uid += 1
        await feed(make_callback_update(uid, ADMIN_ID, "att:present"))
        check("attendance advances to uniform", "Верхняя форма" in session.texts())

        uid += 1
        await feed(make_callback_update(uid, ADMIN_ID, "uni:upper:yes"))
        check("upper uniform advances to lower", "Нижняя форма" in session.texts())

        uid += 1
        await feed(make_callback_update(uid, ADMIN_ID, "uni:lower:yes"))
        check("lower uniform advances to start time", "начала работы" in session.texts())

        uid += 1
        await feed(make_callback_update(uid, ADMIN_ID, "tm:start:9:0"))
        check("start time advances to end time", "окончания работы" in session.texts())

        uid += 1
        await feed(make_callback_update(uid, ADMIN_ID, "tm:end:17:0"))
        check("end time advances to lateness", "Опоздание" in session.texts())

        uid += 1
        await feed(make_callback_update(uid, ADMIN_ID, "rf:late:0"))
        check("lateness advances to early departure", "Ранний уход" in session.texts())

        uid += 1
        await feed(make_callback_update(uid, ADMIN_ID, "rf:early:0"))
        check("early departure advances to notes", "Примечания" in session.texts())

        uid += 1
        await feed(make_callback_update(uid, ADMIN_ID, "rf:notes:0"))
        summary = session.texts()
        check("summary is shown before saving", "Проверьте отчёт" in summary, summary[:150])
        check("summary computed 8 hours", "8.0" in summary, summary[:200])

        uid += 1
        await feed(make_callback_update(uid, ADMIN_ID, "rf:save:1"))
        saved = session.texts()
        check(
            "saving advances to the next coach automatically",
            "Сохранено" in saved or "Готово" in saved,
            saved[:150],
        )

    await bot.session.close()

    print(f"\n{'=' * 52}")
    print(f"  passed: {passed}   failed: {failed}")
    print(f"{'=' * 52}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
