from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

"""
Share a session across different repo to ensure atomicity
"""


class UnitOfWorkRepository:
    def __init__(self, session: AsyncSession = None, sync_session: Session = None):
        self._session = session
        self._sync_session = sync_session

    @property
    def session(self):
        return self._session

    async def flush(self):
        await self._session.flush()

    async def refresh(self, model):
        await self._session.refresh(model)

    async def commit(self):
        await self._session.commit()

    async def rollback(self):
        await self._session.rollback()

    # sync

    @property
    def sync_session(self):
        return self._sync_session

    def sync_flush(self):
        self._sync_session.flush()

    def sync_refresh(self, model):
        self._sync_session.refresh(model)

    def sync_commit(self):
        self._sync_session.commit()

    def sync_rollback(self):
        self._sync_session.rollback()
