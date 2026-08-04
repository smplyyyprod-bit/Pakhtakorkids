"""Router registration.

Order matters: navigation and commands are matched before the stateful flows,
so /cancel and the Home button always work even mid-form.
"""

from aiogram import Router

from app.presentation.telegram.handlers import (
    admin_panel,
    commands,
    manager,
    navigation,
    report_flow,
)


def build_router() -> Router:
    root = Router(name="root")
    root.include_router(commands.router)
    root.include_router(commands.manager_router)
    root.include_router(navigation.router)
    root.include_router(report_flow.router)
    root.include_router(manager.router)
    root.include_router(admin_panel.router)
    return root


__all__ = ["build_router"]
