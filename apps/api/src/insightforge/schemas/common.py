from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class DataEnvelope(BaseModel, Generic[DataT]):
    data: DataT


class PaginationView(StrictSchema):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def from_values(cls, *, page: int, page_size: int, total: int) -> PaginationView:
        total_pages = ceil(total / page_size) if total else 0
        return cls(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )


class CollectionMeta(StrictSchema):
    pagination: PaginationView
    filters: dict[str, object]


class CollectionEnvelope(BaseModel, Generic[DataT]):
    data: list[DataT]
    meta: CollectionMeta
