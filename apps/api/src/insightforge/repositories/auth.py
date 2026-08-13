from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.models import User, UserPreference, UserSession


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def user_by_email(self, email: str) -> User | None:
        return cast(User | None, await self.session.scalar(select(User).where(User.email == email)))

    async def user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def session_by_token_hash(self, token_hash: str) -> tuple[UserSession, User] | None:
        row = (
            await self.session.execute(
                select(UserSession, User)
                .join(User, User.id == UserSession.user_id)
                .where(UserSession.token_hash == token_hash)
            )
        ).one_or_none()
        return row if row is None else (row[0], row[1])

    def add_user(self, user: User, preference: UserPreference) -> None:
        self.session.add_all([user, preference])

    def add_session(self, user_session: UserSession) -> None:
        self.session.add(user_session)
