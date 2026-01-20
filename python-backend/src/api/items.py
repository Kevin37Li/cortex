"""CRUD endpoints for items."""

from fastapi import APIRouter, Depends, Query, Response

from ..db.models import Item, ItemCreate, ItemListResponse, ItemUpdate
from ..db.repositories import ItemRepository
from ..exceptions import ItemNotFoundError
from .deps import get_item_repository

router = APIRouter(prefix="/items", tags=["items"])


@router.post(
    "/",
    response_model=Item,
    status_code=201,
    responses={422: {"description": "Validation error"}},
)
async def create_item(
    data: ItemCreate,
    repo: ItemRepository = Depends(get_item_repository),
) -> Item:
    """Create a new item.

    Returns the created item with generated ID and timestamps.
    """
    return await repo.create(data)


@router.get("/", response_model=ItemListResponse)
async def list_items(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    repo: ItemRepository = Depends(get_item_repository),
) -> ItemListResponse:
    """List items with pagination.

    Returns a paginated list of items ordered by created_at descending.
    """
    items = await repo.list(offset=offset, limit=limit)
    total = await repo.count()
    return ItemListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get(
    "/{id}",
    response_model=Item,
    responses={404: {"description": "Item not found"}},
)
async def get_item(
    id: str,
    repo: ItemRepository = Depends(get_item_repository),
) -> Item:
    """Get a single item by ID."""
    item = await repo.get(id)
    if item is None:
        raise ItemNotFoundError(id)
    return item


@router.put(
    "/{id}",
    response_model=Item,
    responses={404: {"description": "Item not found"}},
)
async def update_item(
    id: str,
    data: ItemUpdate,
    repo: ItemRepository = Depends(get_item_repository),
) -> Item:
    """Update an item.

    Only provided fields are updated. Returns the updated item.
    """
    return await repo.update(id, data)


@router.delete(
    "/{id}",
    status_code=204,
    responses={404: {"description": "Item not found"}},
)
async def delete_item(
    id: str,
    repo: ItemRepository = Depends(get_item_repository),
) -> Response:
    """Delete an item."""
    deleted = await repo.delete(id)
    if not deleted:
        raise ItemNotFoundError(id)
    return Response(status_code=204)
