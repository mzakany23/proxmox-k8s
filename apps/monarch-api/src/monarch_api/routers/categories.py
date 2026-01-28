"""Category and tag endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from monarchmoney import MonarchMoney

from ..auth.dependencies import require_scope
from ..db.models import APIToken
from ..dependencies import get_monarch
from ..schemas.categories import Category, Tag, TagCreate

router = APIRouter(tags=["Categories"])


def _transform_category(raw: dict) -> dict:
    """Transform raw category data to schema format."""
    group = raw.get("group", {}) or {}
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "icon": raw.get("icon"),
        "is_system": raw.get("isSystemCategory", False),
        "is_hidden": raw.get("isHidden", False),
        "group_id": group.get("id"),
        "group_name": group.get("name"),
        "group_type": group.get("type"),
    }


@router.get("/categories", response_model=list[Category])
async def list_categories(
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
    include_hidden: bool = False,
) -> list[Category]:
    """Get all transaction categories."""
    result = await monarch.get_transaction_categories()
    categories = result.get("categories", [])

    if not include_hidden:
        categories = [c for c in categories if not c.get("isHidden", False)]

    return [Category(**_transform_category(c)) for c in categories]


@router.get("/categories/{category_id}", response_model=Category)
async def get_category(
    category_id: str,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
) -> Category:
    """Get a specific category by ID."""
    result = await monarch.get_transaction_categories()
    categories = result.get("categories", [])

    for category in categories:
        if category.get("id") == category_id:
            return Category(**_transform_category(category))

    raise HTTPException(status_code=404, detail=f"Category {category_id} not found")


@router.get("/tags", response_model=list[Tag])
async def list_tags(
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
) -> list[Tag]:
    """Get all transaction tags."""
    result = await monarch.get_transaction_tags()
    tags = result.get("householdTransactionTags", [])

    return [
        Tag(
            id=t.get("id"),
            name=t.get("name"),
            color=t.get("color"),
            order=t.get("order", 0),
        )
        for t in tags
    ]


@router.post("/tags", response_model=Tag)
async def create_tag(
    tag: TagCreate,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("write"))],
) -> Tag:
    """Create a new transaction tag."""
    result = await monarch.create_transaction_tag(name=tag.name)
    created = result.get("createTransactionTag", {}).get("tag", {})

    return Tag(
        id=created.get("id"),
        name=created.get("name"),
        color=created.get("color"),
        order=created.get("order", 0),
    )


@router.get("/tags/{tag_id}", response_model=Tag)
async def get_tag(
    tag_id: str,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
) -> Tag:
    """Get a specific tag by ID."""
    result = await monarch.get_transaction_tags()
    tags = result.get("householdTransactionTags", [])

    for tag in tags:
        if tag.get("id") == tag_id:
            return Tag(
                id=tag.get("id"),
                name=tag.get("name"),
                color=tag.get("color"),
                order=tag.get("order", 0),
            )

    raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")
