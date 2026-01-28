"""Category and tag schemas."""

from pydantic import BaseModel, ConfigDict, Field


class CategoryGroup(BaseModel):
    """A group of related categories."""

    id: str = Field(description="Group identifier")
    name: str = Field(description="Group name")
    type: str = Field(description="Group type (expense, income, transfer)")


class Category(BaseModel):
    """Transaction category."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Category identifier")
    name: str = Field(description="Category name")
    icon: str | None = Field(default=None, description="Category icon")
    is_system: bool = Field(default=False, description="Whether this is a system category")
    is_hidden: bool = Field(default=False, description="Whether category is hidden")
    group_id: str | None = Field(default=None, description="Parent group ID")
    group_name: str | None = Field(default=None, description="Parent group name")
    group_type: str | None = Field(default=None, description="Group type")


class CategoryCreate(BaseModel):
    """Schema for creating a category."""

    name: str = Field(description="Category name")
    group_id: str = Field(description="Parent group ID")
    icon: str | None = Field(default=None, description="Category icon")


class Tag(BaseModel):
    """Transaction tag."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Tag identifier")
    name: str = Field(description="Tag name")
    color: str | None = Field(default=None, description="Tag color")
    order: int = Field(default=0, description="Display order")


class TagCreate(BaseModel):
    """Schema for creating a tag."""

    name: str = Field(description="Tag name")
    color: str | None = Field(default=None, description="Tag color (hex)")
