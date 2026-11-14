from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.schemas.city import CityResponse


class ClientMuseumLocationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    address: str
    latitude: float | None = None
    longitude: float | None = None


class ClientMuseumItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    phone: str | None = None
    email: str | None = None
    city: CityResponse | None = None
    is_favorite: bool = False


class ClientMuseumDetail(ClientMuseumItem):
    locations: list[ClientMuseumLocationItem] = []


class ClientMuseumListResponse(BaseModel):
    items: list[ClientMuseumItem]
    total: int


class ClientEventItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    capacity: int
    date_start: datetime
    date_end: datetime | None = None
    is_recurring: bool
    museum_id: int
    museum_name: str
    location_id: int
    location_name: str | None = None
    location_address: str | None = None
    type_id: int
    type_name: str | None = None
    city: CityResponse | None = None
    is_favorite: bool = False


class ClientEventListResponse(BaseModel):
    items: list[ClientEventItem]
    total: int


class ClientGlobalSearchResponse(BaseModel):
    museums: list[ClientMuseumItem]
    events: list[ClientEventItem]
