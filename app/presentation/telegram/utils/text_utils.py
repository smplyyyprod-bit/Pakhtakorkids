"""Message formatting. All user-facing copy is Russian."""

from datetime import date
from html import escape

from app.domain.models import Branch, Coach, DailyReport
from app.domain.models.daily_report import AttendanceStatus, UniformStatus
from app.infrastructure.repositories import CompletionStats, MonthlyStats
from app.infrastructure.services import CompanyOverview, Rankings

MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

ATTENDANCE_RU = {
    AttendanceStatus.PRESENT: "✅ Присутствует",
    AttendanceStatus.SICK_LEAVE: "🏥 Больничный",
    AttendanceStatus.VACATION: "🏖 Отпуск",
    AttendanceStatus.UNEXCUSED_ABSENCE: "❌ Неуважительная причина",
    AttendanceStatus.NOT_FILLED: "⚠️ Не заполнено",
}

UNIFORM_RU = {
    UniformStatus.YES: "✅ Да",
    UniformStatus.NO: "❌ Нет",
    UniformStatus.NO_DATA: "❔ Нет данных",
}


def esc(value: object) -> str:
    """Escape for Telegram HTML parse mode.

    Coach names are operator-entered free text; without escaping, a name
    containing `<` would break the message markup.
    """
    return escape(str(value), quote=False)


def month_name(month: int) -> str:
    return MONTHS_RU[month - 1]


def fmt_hours(value: float) -> str:
    return f"{float(value):.1f}".replace(".0", "")


def format_report(report: DailyReport, coach: Coach, branch: Branch | None) -> str:
    """Full daily record, including the placeholder state."""
    lines = [
        "📋 <b>Ежедневный отчёт</b>",
        "",
        f"👤 <b>Тренер:</b> {esc(coach.full_name)}",
        f"🏢 <b>Отделение:</b> {esc(branch.name) if branch else '—'}",
        f"📅 <b>Дата:</b> {report.report_date.strftime('%d.%m.%Y')}",
        "",
        f"<b>Присутствие:</b> {ATTENDANCE_RU.get(report.attendance, '—')}",
        f"<b>Верхняя форма:</b> {UNIFORM_RU.get(report.upper_uniform, '—')}",
        f"<b>Нижняя форма:</b> {UNIFORM_RU.get(report.lower_uniform, '—')}",
        "",
        f"🕐 <b>Начало:</b> {report.start_time.strftime('%H:%M') if report.start_time else '—'}",
        f"🕑 <b>Окончание:</b> {report.end_time.strftime('%H:%M') if report.end_time else '—'}",
        f"⏱ <b>Отработано часов:</b> {fmt_hours(report.worked_hours or 0)}",
        "",
        f"⏰ <b>Опоздание:</b> {report.late_arrival_minutes} мин",
        f"🚪 <b>Ранний уход:</b> {report.early_departure_minutes} мин",
    ]
    if report.notes:
        lines += ["", f"📝 <b>Примечания:</b> {esc(report.notes)}"]
    if report.admin_comments:
        lines.append(f"💬 <b>Комментарий:</b> {esc(report.admin_comments)}")

    lines += [
        "",
        "<b>Статус:</b> "
        + ("✅ Заполнен" if report.is_completed else "⚠️ Не заполнен"),
    ]
    return "\n".join(lines)


def format_incomplete_notice(report: DailyReport) -> str:
    """The 'never completed' view a manager sees for a missing report."""
    coach_name = esc(report.coach.full_name) if report.coach else "—"
    return (
        f"⚠️ <b>Тренер:</b> {coach_name}\n"
        f"<b>Дата:</b> {report.report_date.strftime('%d.%m.%Y')}\n\n"
        "<b>Статус:</b> ежедневный отчёт не заполнен\n"
        "Отработано часов: 0\n"
        "Присутствие: не заполнено\n"
        "Верхняя форма: нет данных\n"
        "Нижняя форма: нет данных"
    )


def format_monthly_stats(stats: MonthlyStats, coach_name: str, year: int, month: int) -> str:
    return "\n".join([
        "📊 <b>Месячная статистика</b>",
        "",
        f"👤 <b>Тренер:</b> {esc(coach_name)}",
        f"📅 <b>Период:</b> {month_name(month)} {year}",
        "",
        f"• Отработано часов: <b>{fmt_hours(stats.worked_hours)}</b>",
        f"• Отработано дней: <b>{stats.worked_days}</b>",
        f"• Дней без верхней формы: <b>{stats.days_without_upper_uniform}</b>",
        f"• Дней без нижней формы: <b>{stats.days_without_lower_uniform}</b>",
        f"• Опозданий: <b>{stats.late_arrivals}</b>",
        f"• Всего минут опоздания: <b>{stats.total_late_minutes}</b>",
        f"• Ранних уходов: <b>{stats.early_departures}</b>",
        f"• Всего минут раннего ухода: <b>{stats.total_early_departure_minutes}</b>",
        f"• Дней болезни: <b>{stats.sick_days}</b>",
        f"• Дней отпуска: <b>{stats.vacation_days}</b>",
        f"• Неуважительных отсутствий: <b>{stats.unexcused_absences}</b>",
        "",
        f"⚠️ Незаполненных дней: <b>{stats.not_filled_days}</b> из {stats.total_days}",
    ])


def format_completion(stats: CompletionStats, label: str) -> str:
    return "\n".join([
        f"📋 <b>Заполнение отчётов — {esc(label)}</b>",
        "",
        f"Ожидается отчётов: <b>{stats.expected}</b>",
        f"Заполнено: <b>{stats.completed}</b>",
        f"Не заполнено: <b>{stats.missing}</b>",
        f"Процент заполнения: <b>{stats.percentage}%</b>",
    ])


def format_dashboard(overview: CompanyOverview, year: int, month: int) -> str:
    return "\n".join([
        "📈 <b>Панель управления</b>",
        f"<i>{month_name(month)} {year}</i>",
        "",
        "<b>Обзор компании</b>",
        f"• Всего тренеров: <b>{overview.total_coaches}</b>",
        f"• Отработано часов: <b>{fmt_hours(overview.total_worked_hours)}</b>",
        f"• Процент явки: <b>{overview.attendance_percentage}%</b>",
        f"• Дней болезни: <b>{overview.total_sick_days}</b>",
        f"• Неуважительных отсутствий: <b>{overview.total_absences}</b>",
        "",
        "<b>Заполнение отчётов</b>",
        f"• Ожидается: <b>{overview.completion.expected}</b>",
        f"• Заполнено: <b>{overview.completion.completed}</b>",
        f"• Не заполнено: <b>{overview.completion.missing}</b>",
        f"• Процент: <b>{overview.completion.percentage}%</b>",
    ])


def _ranking_block(title: str, rows: list[MonthlyStats], value_fn, unit: str) -> str:
    if not rows:
        return f"<b>{title}</b>\n<i>нет данных</i>"
    medals = ["🥇", "🥈", "🥉"]
    lines = [f"<b>{title}</b>"]
    for index, item in enumerate(rows[:5]):
        marker = medals[index] if index < len(medals) else f"{index + 1}."
        lines.append(
            f"{marker} {esc(item.coach_name or item.coach_id)} — {value_fn(item)} {unit}"
        )
    return "\n".join(lines)


def format_rankings(rankings: Rankings, year: int, month: int) -> str:
    blocks = [
        f"🔍 <b>Аналитика — {month_name(month)} {year}</b>",
        "",
        _ranking_block(
            "⏱ Больше всего часов",
            rankings.most_worked_hours,
            lambda s: fmt_hours(s.worked_hours),
            "ч",
        ),
        "",
        _ranking_block(
            "🎯 Самые пунктуальные",
            rankings.most_punctual,
            lambda s: s.total_late_minutes,
            "мин опозданий",
        ),
        "",
        _ranking_block(
            "⏰ Больше всего опозданий",
            rankings.most_late_arrivals,
            lambda s: s.total_late_minutes,
            "мин",
        ),
        "",
        _ranking_block(
            "👕 Нарушения формы",
            rankings.most_uniform_violations,
            lambda s: s.uniform_violations,
            "дн.",
        ),
    ]
    return "\n".join(blocks)


def format_comparison(rows: list[MonthlyStats], year: int, month: int) -> str:
    if not rows:
        return "Нет данных за выбранный период."

    lines = [
        f"⚖️ <b>Сравнение тренеров — {month_name(month)} {year}</b>",
        "",
        "<code>Часы  Дни  Опозд.  Тренер</code>",
    ]
    for item in rows[:30]:
        lines.append(
            "<code>"
            f"{fmt_hours(item.worked_hours):>5} "
            f"{item.worked_days:>4} "
            f"{item.total_late_minutes:>6}  "
            "</code>"
            f"{esc(item.coach_name)}"
        )
    if len(rows) > 30:
        lines.append(f"\n<i>…и ещё {len(rows) - 30}</i>")
    return "\n".join(lines)


def format_trend(rows: list[dict[str, object]], year: int, month: int) -> str:
    """Compact per-day trend rendered as a text bar chart."""
    if not rows:
        return "Нет данных за выбранный период."

    lines = [f"📉 <b>Динамика явки — {month_name(month)} {year}</b>", ""]
    peak = max((int(r["total"]) for r in rows), default=0) or 1
    for row in rows:
        present = int(row["present"])
        filled = round(present / peak * 10)
        bar = "█" * filled + "░" * (10 - filled)
        day: date = row["day"]  # type: ignore[assignment]
        lines.append(
            f"<code>{day.strftime('%d.%m')} {bar}</code> "
            f"{present}/{int(row['total'])} · {fmt_hours(float(row['hours']))}ч"
        )
    return "\n".join(lines)


def format_coach_card(coach: Coach) -> str:
    status = "✅ активен" if coach.is_active else "⛔️ неактивен"
    return "\n".join([
        f"👤 <b>{esc(coach.full_name)}</b>",
        "",
        f"<b>Табельный номер:</b> {esc(coach.unique_id)}",
        f"<b>Должность:</b> {esc(coach.position)}",
        f"<b>Команда:</b> {esc(coach.team)}",
        f"<b>Отделение:</b> {esc(coach.branch.name) if coach.branch else '—'}",
        f"<b>Статус:</b> {status}",
    ])
