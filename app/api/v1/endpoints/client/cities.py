from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_city_service
from app.schemas.city import CityListResponse, CityResponse
from app.services.city import CityService

router = APIRouter(prefix="/client/cities", tags=["Client Cities"])


@router.get(
    "",
    response_model=CityListResponse,
    status_code=status.HTTP_200_OK,
    summary="Список доступных городов для PWA",
    description="Возвращает список активных городов для выбора пользователем в приложении",
)
async def list_client_cities(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: CityService = Depends(get_city_service),
) -> CityListResponse:
    items, total = await service.list_cities(
        is_active=True,
        offset=offset,
        limit=limit,
    )
    return CityListResponse(
        items=[CityResponse.model_validate(c) for c in items],
        total=total,
    )
