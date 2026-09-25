"""Database sessions for request handlers.

The application's lifespan creates one asynchronous engine and a session factory on ``app.state``;
handlers receive a session per request through the ``session`` dependency.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessions() as s:
        yield s
