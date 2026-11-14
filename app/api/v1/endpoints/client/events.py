from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    get_client_catalog_service,
    get_optional_client_user,
)
from app.db.models.client_user import ClientUser
from app.exceptions.schemas import ErrorResponse
from app.schemas.client_catalog import ClientEventItem, ClientEventListResponse
from app.services.client_catalog import ClientCatalogService

router = APIRouter(prefix="/client/events", tags=["Client Events"])


@router.get(
    "",
    response_model=ClientEventListResponse,
    status_code=status.HTTP_200_OK,
    summary="Афиша событий для PWA",
    description="Возвращает список опубликованных событий. Город автоматически подставляется из профиля текущего пользователя.",
)
async def list_events(
    museum_id: int | None = Query(None, description="Фильтр по ID музея"),
    query: str | None = Query(None, description="Поисковый запрос по названию или описанию"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: ClientUser | None = Depends(get_optional_client_user),
    service: ClientCatalogService = Depends(get_client_catalog_service),
) -> ClientEventListResponse:
    city_id = current_user.city_id if current_user else None
    user_id = current_user.id if current_user else None
    items, total = await service.list_events(
        city_id=city_id,
        museum_id=museum_id,
        query=query,
        offset=offset,
        limit=limit,
        user_id=user_id,
    )
    return ClientEventListResponse(items=items, total=total)


@router.get(
    "/{event_id}",
    response_model=ClientEventItem,
    status_code=status.HTTP_200_OK,
    summary="Детальная карточка события",
    description="Возвращает полную информацию об опубликованном событии, включая локацию и музей",
    responses={
        404: {"model": ErrorResponse, "description": "Event not found"},
    },
)
async def get_event(
    event_id: int,
    current_user: ClientUser | None = Depends(get_optional_client_user),
    service: ClientCatalogService = Depends(get_client_catalog_service),
) -> ClientEventItem:
    user_id = current_user.id if current_user else None
    return await service.get_event(event_id, user_id=user_id)
