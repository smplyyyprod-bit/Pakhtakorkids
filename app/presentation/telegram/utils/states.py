"""FSM state definitions.

State data holds only primitives - IDs, dates as ISO strings, ints. ORM objects
are never stored: aiogram serialises state data, and a detached SQLAlchemy
instance blows up the moment a handler touches a lazy relationship on it.
"""

from aiogram.fsm.state import State, StatesGroup


class ReportForm(StatesGroup):
    """The daily evaluation form, one state per question."""

    choosing_branch = State()
    choosing_coach = State()
    attendance = State()
    upper_uniform = State()
    lower_uniform = State()
    start_time = State()
    start_time_input = State()
    end_time = State()
    end_time_input = State()
    late_minutes = State()
    late_minutes_input = State()
    early_minutes = State()
    early_minutes_input = State()
    notes = State()
    notes_input = State()
    confirming = State()


class ManagerFlow(StatesGroup):
    """Manager navigation: branch → coach → month."""

    choosing_branch = State()
    choosing_coach = State()
    choosing_month = State()


class AdminPanel(StatesGroup):
    """Coach and branch administration."""

    menu = State()
    coach_name = State()
    coach_unique_id = State()
    coach_position = State()
    coach_team = State()
    coach_branch = State()
    branch_name = State()
    branch_description = State()
    criterion_name = State()
    criterion_type = State()
