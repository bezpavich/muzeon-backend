from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    get_client_catalog_service,
    get_optional_client_user,
)
from app.db.models.client_user import ClientUser
from app.exceptions.schemas import ErrorResponse
from app.schemas.client_catalog import ClientMuseumDetail, ClientMuseumListResponse
from app.services.client_catalog import ClientCatalogService

router = APIRouter(prefix="/client/museums", tags=["Client Museums"])


@router.get(
    "",
    response_model=ClientMuseumListResponse,
    status_code=status.HTTP_200_OK,
    summary="Каталог музеев для PWA",
    description="Возвращает список активных музеев. Город автоматически подставляется из профиля текущего пользователя.",
)
async def list_museums(
    query: str | None = Query(None, description="Поисковый запрос по названию"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: ClientUser | None = Depends(get_optional_client_user),
    service: ClientCatalogService = Depends(get_client_catalog_service),
) -> ClientMuseumListResponse:
    city_id = current_user.city_id if current_user else None
    user_id = current_user.id if current_user else None
    items, total = await service.list_museums(
        city_id=city_id,
        query=query,
        offset=offset,
        limit=limit,
        user_id=user_id,
    )
    return ClientMuseumListResponse(items=items, total=total)


@router.get(
    "/{museum_id}",
    response_model=ClientMuseumDetail,
    status_code=status.HTTP_200_OK,
    summary="Детальная информация о музее",
    description="Возвращает карточку музея с адресом, контактами и активными площадками",
    responses={
        404: {"model": ErrorResponse, "description": "Museum not found"},
    },
)
async def get_museum(
    museum_id: int,
    current_user: ClientUser | None = Depends(get_optional_client_user),
    service: ClientCatalogService = Depends(get_client_catalog_service),
) -> ClientMuseumDetail:
    user_id = current_user.id if current_user else None
    return await service.get_museum(museum_id, user_id=user_id)
