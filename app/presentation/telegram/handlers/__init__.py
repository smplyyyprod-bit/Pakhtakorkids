from app.presentation.telegram.handlers.start_handler import router as start_router
from app.presentation.telegram.handlers.admin_handler import router as admin_router
from app.presentation.telegram.handlers.manager_handler import router as manager_router
from app.presentation.telegram.handlers.report_handler import router as report_router

__all__ = [
    "start_router",
    "admin_router",
    "manager_router",
    "report_router",
]
