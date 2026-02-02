"""CRUD endpoints for items."""

import aiosqlite
from fastapi import APIRouter, Depends, Query, Response

from ..db.models import Item, ItemCreate, ItemListResponse, ItemUpdate
from ..db.repositories import ItemRepository
from ..exceptions import ItemNotFoundError
from .deps import get_db_connection, get_item_repo

router = APIRouter(prefix="/items", tags=["items"])


@router.post(
    "/",
    response_model=Item,
    status_code=201,
    responses={422: {"description": "Validation error"}},
)
async def create_item(
    data: ItemCreate,
    db: aiosqlite.Connection = Depends(get_db_connection),
    repo: ItemRepository = Depends(get_item_repo),
) -> Item:
    """Create a new item.

    Returns the created item with generated ID and timestamps.
    """
    item = await repo.create(db, data)
    await db.commit()
    return item


@router.get("/", response_model=ItemListResponse)
async def list_items(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: aiosqlite.Connection = Depends(get_db_connection),
    repo: ItemRepository = Depends(get_item_repo),
) -> ItemListResponse:
    """List items with pagination.

    Returns a paginated list of items ordered by created_at descending.
    """
    items = await repo.list(db, offset=offset, limit=limit)
    total = await repo.count(db)
    return ItemListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get(
    "/{id}",
    response_model=Item,
    responses={404: {"description": "Item not found"}},
)
async def get_item(
    id: str,
    db: aiosqlite.Connection = Depends(get_db_connection),
    repo: ItemRepository = Depends(get_item_repo),
) -> Item:
    """Get a single item by ID."""
    item = await repo.get(db, id)
    if item is None:
        raise ItemNotFoundError(item_id=id)
    return item


@router.put(
    "/{id}",
    response_model=Item,
    responses={404: {"description": "Item not found"}},
)
async def update_item(
    id: str,
    data: ItemUpdate,
    db: aiosqlite.Connection = Depends(get_db_connection),
    repo: ItemRepository = Depends(get_item_repo),
) -> Item:
    """Update an item.

    Only provided fields are updated. Returns the updated item.
    """
    item = await repo.update(db, id, data)
    await db.commit()
    return item


@router.delete(
    "/{id}",
    status_code=204,
    responses={404: {"description": "Item not found"}},
)
async def delete_item(
    id: str,
    db: aiosqlite.Connection = Depends(get_db_connection),
    repo: ItemRepository = Depends(get_item_repo),
) -> Response:
    """Delete an item."""
    deleted = await repo.delete(db, id)
    if not deleted:
        raise ItemNotFoundError(item_id=id)
    await db.commit()
    return Response(status_code=204)
