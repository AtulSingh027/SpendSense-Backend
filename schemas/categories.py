from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CategoryCreate(BaseModel):
    name: str = Field(..., max_length=50, min_length=1, description="Name of the category")
    icon: str | None = Field(None, max_length=50, description="Icon representing the category")


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, max_length=50, min_length=1, description="Name of the category")
    icon: str | None = Field(None, max_length=50, description="Icon representing the category")


class CategoryResponse(BaseModel):
    id: int
    user_id: int | None = None
    name: str
    icon: str | None = None
    is_system: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
