from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.city import CityResponse


class ClientUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    name: str | None = None
    is_active: bool
    city: CityResponse | None = None
    created_at: datetime
    updated_at: datetime


class ClientUserUpdate(BaseModel):
    name: str | None = None
    city_id: int | None = None
