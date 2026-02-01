"""Base repository class for database operations."""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.db.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Base repository with common CRUD operations."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        """Get a record by ID."""
        return await self.session.get(self.model, id)

    async def get_all(
        self, *, skip: int = 0, limit: int = 100
    ) -> list[ModelT]:
        """Get all records with pagination."""
        query = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Get total count of records."""
        query = select(func.count()).select_from(self.model)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, **kwargs: Any) -> ModelT:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(
        self, id: uuid.UUID, **kwargs: Any
    ) -> ModelT | None:
        """Update a record by ID."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        return instance

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete a record by ID."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True
