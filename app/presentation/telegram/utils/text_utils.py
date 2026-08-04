from app.domain.models import DailyReport


def format_report_text(report: DailyReport) -> str:
    """Format daily report as text message."""
    text = f"""
📋 **Отчет о работе**

👤 **Тренер:** {report.coach.full_name}
🏢 **Отделение:** {report.branch.name}
📅 **Дата:** {report.report_date.strftime('%d.%m.%Y')}

**Присутствие:** {report.attendance.value}
**Верхняя форма:** {report.upper_uniform.value}
**Нижняя форма:** {report.lower_uniform.value}

**Время работы:**
🕐 Начало: {report.start_time or '—'}
🕑 Окончание: {report.end_time or '—'}
⏱️ Всего часов: {report.worked_hours or 0}

**Производительность:**
⏰ Опоздания (мин): {report.late_arrival_minutes}
🚪 Ранний уход (мин): {report.early_departure_minutes}

**Примечания:**
{report.notes or 'Нет примечаний'}

**Статус:** {'✅ Заполнен' if report.is_completed else '⏳ Не заполнен'}
"""
    return text


def format_monthly_stats_text(coach_name: str, year: int, month: int, stats: dict) -> str:
    """Format monthly statistics as text message."""
    text = f"""
📊 **Ежемесячный отчет**

👤 **Тренер:** {coach_name}
📅 **Месяц:** {month}/{year}

**Основные показатели:**
⏱️ Отработано часов: {stats['worked_hours']}
📅 Отработано дней: {stats['worked_days']}

**Дисциплина:**
⏰ Опозданий: {stats['late_arrivals']}
⏱️ Всего минут опоздания: {stats['total_late_minutes']}
🚪 Ранних уходов: {stats['early_departures']}
⏱️ Всего минут раннего ухода: {stats['total_early_departure_minutes']}

**Форма:**
👕 Дней без верхней формы: {stats['days_without_upper_uniform']}
👖 Дней без нижней формы: {stats['days_without_lower_uniform']}

**Отсутствия:**
🏥 Дней болезни: {stats['sick_days']}
🏖️ Дней отпуска: {stats['vacation_days']}
❌ Дней без объяснения причины: {stats['unexcused_absences']}
"""
    return text


def format_company_overview_text(overview: dict) -> str:
    """Format company overview statistics."""
    text = f"""
🏢 **Обзор компании**

👥 **Всего тренеров:** {overview['total_coaches']}
⏱️ **Всего отработано часов:** {overview['total_worked_hours']}
📊 **Процент явки:** {overview['attendance_percentage']}%
🏥 **Всего дней болезни:** {overview['total_sick_days']}
❌ **Всего отсутствий:** {overview['total_absences']}

**Отчеты:**
✅ Заполнено: {overview['reports_completed']}
📋 Всего: {overview['reports_total']}
"""
    return text
