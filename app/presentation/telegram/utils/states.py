from aiogram.fsm.state import State, StatesGroup


class ReportFormStates(StatesGroup):
    """States for daily report form."""

    selecting_branch = State()
    selecting_coach = State()
    filling_attendance = State()
    filling_upper_uniform = State()
    filling_lower_uniform = State()
    filling_start_time = State()
    filling_end_time = State()
    filling_late_minutes = State()
    filling_early_minutes = State()
    filling_notes = State()
    reviewing_report = State()


class AdminPanelStates(StatesGroup):
    """States for admin panel."""

    selecting_action = State()
    adding_coach = State()
    editing_coach = State()
    deleting_coach = State()
    adding_branch = State()
    editing_branch = State()
    deleting_branch = State()


class ManagerStates(StatesGroup):
    """States for manager panel."""

    selecting_branch = State()
    selecting_coach = State()
    selecting_month = State()
    viewing_stats = State()
