from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject

from database import Database


class SessionPersistenceMiddleware(BaseMiddleware):
    """Restores and snapshots each user's FSM state in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        state: FSMContext | None = data.get("state")
        if user and state and await state.get_state() is None:
            saved = await self.db.get_session(user.id)
            if saved and saved["state"] != "idle":
                await state.set_state(saved["state"])
                await state.set_data(saved["data"])
        result = await handler(event, data)
        if user and state:
            current = await state.get_state()
            await self.db.save_session(user.id, current or "idle", await state.get_data())
        return result
