from datetime import time

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import AttendanceStatus, UniformStatus
from app.infrastructure.database import SessionLocal
from app.infrastructure.services import DailyReportService, CoachService
from app.presentation.telegram.keyboards.report_keyboards import (
    get_attendance_keyboard,
    get_uniform_keyboard,
    get_quick_time_keyboard,
    get_yes_no_keyboard,
    get_report_confirmation_keyboard,
)
from app.presentation.telegram.keyboards import get_back_and_home_buttons
from app.presentation.telegram.utils import ReportFormStates
from app.presentation.telegram.utils.text_utils import format_report_text

logger = get_logger()
router = Router()


@router.callback_query(F.data.startswith("attendance_"), ReportFormStates.filling_attendance)
async def handle_attendance_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle attendance status selection."""
    attendance_map = {
        "attendance_present": AttendanceStatus.PRESENT,
        "attendance_sick": AttendanceStatus.SICK_LEAVE,
        "attendance_vacation": AttendanceStatus.VACATION,
        "attendance_absent": AttendanceStatus.UNEXCUSED_ABSENCE,
    }

    attendance = attendance_map.get(callback.data)
    if not attendance:
        await callback.answer("❌ Ошибка выбора.", show_alert=True)
        return

    data = await state.get_data()
    await state.update_data(attendance=attendance)

    keyboard = get_uniform_keyboard()
    await callback.message.edit_text(
        "👕 Выберите статус верхней формы:",
        reply_markup=keyboard,
    )
    await state.set_state(ReportFormStates.filling_upper_uniform)
    await callback.answer()


@router.callback_query(F.data.startswith("uniform_"), ReportFormStates.filling_upper_uniform)
async def handle_upper_uniform_selection(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Handle upper uniform status selection."""
    uniform_map = {
        "uniform_yes": UniformStatus.YES,
        "uniform_no": UniformStatus.NO,
        "uniform_no_data": UniformStatus.NO_DATA,
    }

    uniform = uniform_map.get(callback.data)
    if not uniform:
        await callback.answer("❌ Ошибка выбора.", show_alert=True)
        return

    await state.update_data(upper_uniform=uniform)

    keyboard = get_uniform_keyboard()
    await callback.message.edit_text(
        "👖 Выберите статус нижней формы:",
        reply_markup=keyboard,
    )
    await state.set_state(ReportFormStates.filling_lower_uniform)
    await callback.answer()


@router.callback_query(F.data.startswith("uniform_"), ReportFormStates.filling_lower_uniform)
async def handle_lower_uniform_selection(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Handle lower uniform status selection."""
    uniform_map = {
        "uniform_yes": UniformStatus.YES,
        "uniform_no": UniformStatus.NO,
        "uniform_no_data": UniformStatus.NO_DATA,
    }

    uniform = uniform_map.get(callback.data)
    if not uniform:
        await callback.answer("❌ Ошибка выбора.", show_alert=True)
        return

    await state.update_data(lower_uniform=uniform)

    keyboard = get_quick_time_keyboard()
    await callback.message.edit_text(
        "🕐 Выберите время начала работы (или введите вручную):",
        reply_markup=keyboard,
    )
    await state.set_state(ReportFormStates.filling_start_time)
    await callback.answer()


@router.callback_query(F.data.startswith("time_"), ReportFormStates.filling_start_time)
async def handle_start_time_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle start time selection."""
    time_str = callback.data.split("_")[1]
    hour = int(time_str[:2])
    minute = int(time_str[2:])

    start_time = time(hour=hour, minute=minute)
    await state.update_data(start_time=start_time)

    keyboard = get_quick_time_keyboard()
    await callback.message.edit_text(
        f"🕑 Время начала установлено: {start_time.strftime('%H:%M')}\n\nВыберите время окончания работы:",
        reply_markup=keyboard,
    )
    await state.set_state(ReportFormStates.filling_end_time)
    await callback.answer()


@router.callback_query(F.data.startswith("time_"), ReportFormStates.filling_end_time)
async def handle_end_time_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle end time selection."""
    time_str = callback.data.split("_")[1]
    hour = int(time_str[:2])
    minute = int(time_str[2:])

    end_time = time(hour=hour, minute=minute)
    await state.update_data(end_time=end_time)

    data = await state.get_data()
    start_time = data.get("start_time")

    async with SessionLocal() as session:
        report_service = DailyReportService(session)
        if start_time and end_time:
            worked_hours = await report_service.calculate_worked_hours(
                start_time, end_time
            )
            await state.update_data(worked_hours=worked_hours)

    keyboard = get_quick_time_keyboard()
    keyboard.inline_keyboard = [
        [keyboard.inline_keyboard[0][0]],  # First time option
        [keyboard.inline_keyboard[-1][0]],  # Input time button
        [keyboard.inline_keyboard[-1][1]],  # Back button
    ]

    await callback.message.edit_text(
        f"🕑 Время окончания установлено: {end_time.strftime('%H:%M')}\n\nВведите минуты опоздания (или 0):",
        reply_markup=keyboard,
    )
    await state.set_state(ReportFormStates.filling_late_minutes)
    await callback.answer()


@router.message(ReportFormStates.filling_late_minutes)
async def handle_late_minutes_input(message: Message, state: FSMContext) -> None:
    """Handle late minutes input."""
    try:
        late_minutes = int(message.text)
        if late_minutes < 0:
            await message.answer("❌ Введите положительное число.")
            return

        await state.update_data(late_minutes=late_minutes)

        keyboard = get_quick_time_keyboard()
        keyboard.inline_keyboard = [
            [keyboard.inline_keyboard[0][0]],  # First time option
            [keyboard.inline_keyboard[-1][0]],  # Input time button
        ]

        await message.answer(
            "🚪 Введите минуты раннего ухода (или 0):",
            reply_markup=keyboard,
        )
        await state.set_state(ReportFormStates.filling_early_minutes)

    except ValueError:
        await message.answer("❌ Введите корректное число.")


@router.message(ReportFormStates.filling_early_minutes)
async def handle_early_minutes_input(message: Message, state: FSMContext) -> None:
    """Handle early departure minutes input."""
    try:
        early_minutes = int(message.text)
        if early_minutes < 0:
            await message.answer("❌ Введите положительное число.")
            return

        await state.update_data(early_minutes=early_minutes)

        await message.answer(
            "📝 Введите примечания (или пропустите):",
        )
        await state.set_state(ReportFormStates.filling_notes)

    except ValueError:
        await message.answer("❌ Введите корректное число.")


@router.message(ReportFormStates.filling_notes)
async def handle_notes_input(message: Message, state: FSMContext) -> None:
    """Handle notes input."""
    notes = message.text if message.text and message.text != "/skip" else None

    await state.update_data(notes=notes)

    data = await state.get_data()

    async with SessionLocal() as session:
        report_service = DailyReportService(session)
        coach_service = CoachService(session)

        coach_id = data.get("coach_id")
        report_id = data.get("report_id")

        coach = await coach_service.get_coach(coach_id)
        report = await report_service.get_report(coach_id, report_id)

        # Update report with all data
        report = await report_service.create_or_update_report(
            coach_id=coach_id,
            branch_id=data.get("branch_id"),
            report_date=report.report_date,
            attendance=data.get("attendance"),
            upper_uniform=data.get("upper_uniform"),
            lower_uniform=data.get("lower_uniform"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            worked_hours=data.get("worked_hours"),
            late_arrival_minutes=data.get("late_minutes", 0),
            early_departure_minutes=data.get("early_minutes", 0),
            notes=notes,
            completed_by_user_id=message.from_user.id,
        )

        await state.update_data(current_report=report)

    keyboard = get_report_confirmation_keyboard()
    await message.answer(
        format_report_text(report),
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(ReportFormStates.reviewing_report)


@router.callback_query(F.data == "save_report", ReportFormStates.reviewing_report)
async def handle_save_report(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle save report."""
    data = await state.get_data()
    report = data.get("current_report")

    await callback.message.edit_text(
        f"✅ Отчет для {report.coach.full_name} успешно сохранен!\n\n"
        "Переходим к следующему тренеру...",
    )

    # Show next coach
    coaches = data.get("coaches", [])
    current_index = data.get("current_coach_index", 0)

    if current_index + 1 < len(coaches):
        await state.update_data(current_coach_index=current_index + 1)
        await state.set_state(ReportFormStates.selecting_coach)

        next_coach = coaches[current_index + 1]
        from app.presentation.telegram.keyboards.coach_keyboards import (
            get_coaches_pagination_keyboard,
        )

        keyboard = await get_coaches_pagination_keyboard(coaches, page=0)
        await callback.message.answer(
            f"👤 Следующий тренер: {next_coach.full_name}\n\n"
            "Нажмите на имя для начала заполнения отчета.",
            reply_markup=keyboard,
        )
    else:
        await callback.message.answer(
            "✅ Все отчеты в отделении заполнены!\n\n"
            "Спасибо за проделанную работу.",
        )
        await state.clear()

    await callback.answer()


@router.callback_query(F.data == "cancel_report", ReportFormStates.reviewing_report)
async def handle_cancel_report(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle cancel report."""
    await callback.message.edit_text("❌ Отчет отменен. Возвращаемся в главное меню...")
    await state.clear()
    await callback.answer()
