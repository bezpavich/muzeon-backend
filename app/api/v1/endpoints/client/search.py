from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    get_client_catalog_service,
    get_optional_client_user,
)
from app.db.models.client_user import ClientUser
from app.schemas.client_catalog import ClientGlobalSearchResponse
from app.services.client_catalog import ClientCatalogService

router = APIRouter(prefix="/client/search", tags=["Client Search"])


@router.get(
    "",
    response_model=ClientGlobalSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Сквозной глобальный поиск по музеям и событиям",
    description="Ищет одновременно по активным музеям и опубликованным событиям с учётом города из профиля текущего пользователя",
)
async def global_search(
    query: str = Query(..., min_length=1, description="Поисковый запрос"),
    limit: int = Query(10, ge=1, le=50, description="Максимальное количество результатов в каждой категории"),
    current_user: ClientUser | None = Depends(get_optional_client_user),
    service: ClientCatalogService = Depends(get_client_catalog_service),
) -> ClientGlobalSearchResponse:
    city_id = current_user.city_id if current_user else None
    user_id = current_user.id if current_user else None
    return await service.global_search(
        query=query,
        city_id=city_id,
        limit=limit,
        user_id=user_id,
    )
