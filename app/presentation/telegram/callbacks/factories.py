"""Typed callback data.

aiogram's CallbackData factory parses and validates the payload, so handlers
receive typed fields instead of splitting strings on underscores - which breaks
the moment a value itself contains one.

Telegram caps callback_data at 64 bytes, so prefixes are kept short.
"""

from aiogram.filters.callback_data import CallbackData


class NavCB(CallbackData, prefix="nav"):
    """Navigation between menus."""

    target: str  # home | back | cancel | noop


class PageCB(CallbackData, prefix="pg"):
    """Pagination within a listing."""

    scope: str  # branches | coaches | reports
    page: int
    ref_id: int = 0


class BranchCB(CallbackData, prefix="br"):
    action: str  # pick | stats | admin | toggle
    branch_id: int


class CoachCB(CallbackData, prefix="co"):
    action: str  # fill | view | stats | edit | toggle | move
    coach_id: int


class MonthCB(CallbackData, prefix="mo"):
    """Month selection for statistics and exports."""

    action: str  # stats | export | dashboard | compare
    year: int
    month: int
    ref_id: int = 0


class AttendanceCB(CallbackData, prefix="att"):
    value: str  # present | sick | vacation | absent


class UniformCB(CallbackData, prefix="uni"):
    slot: str  # upper | lower
    value: str  # yes | no | nodata


class TimeCB(CallbackData, prefix="tm"):
    slot: str  # start | end
    hour: int
    minute: int


class ReportFieldCB(CallbackData, prefix="rf"):
    """Numeric and free-text steps of the report form."""

    field: str  # late | early | notes
    value: int = 0


class ExportCB(CallbackData, prefix="ex"):
    fmt: str  # xlsx | pdf
    coach_id: int
    year: int
    month: int


class AdminActionCB(CallbackData, prefix="adm"):
    action: str  # coaches | branches | criteria | add_coach | ...
    ref_id: int = 0
