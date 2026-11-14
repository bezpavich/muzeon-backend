from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    alias: str | None = Field(default=None, max_length=100)
    is_active: bool = True


class CityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    alias: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


class CityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    alias: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CityListResponse(BaseModel):
    items: list[CityResponse]
    total: int
