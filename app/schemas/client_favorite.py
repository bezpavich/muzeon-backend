from pydantic import BaseModel

from app.schemas.client_catalog import ClientEventItem, ClientMuseumItem


class ClientFavoriteStatus(BaseModel):
    is_favorite: bool


class ClientFavoriteIdsResponse(BaseModel):
    museum_ids: list[int]
    event_ids: list[int]


class ClientFavoritesResponse(BaseModel):
    museums: list[ClientMuseumItem]
    events: list[ClientEventItem]
