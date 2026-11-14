from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_city_service, get_current_superadmin
from app.exceptions.schemas import ErrorResponse
from app.schemas.city import CityCreate, CityListResponse, CityResponse, CityUpdate
from app.services.city import CityService

router = APIRouter(prefix="/admin/cities", tags=["Admin Cities"])


@router.get(
    "",
    response_model=CityListResponse,
    status_code=status.HTTP_200_OK,
    summary="Список городов",
    description="Возвращает список всех городов с пагинацией и опциональным фильтром по активности",
    dependencies=[Depends(get_current_superadmin)],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    },
)
async def list_cities(
    is_active: bool | None = Query(None, description="Фильтр по статусу активности"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: CityService = Depends(get_city_service),
) -> CityListResponse:
    items, total = await service.list_cities(
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    return CityListResponse(
        items=[CityResponse.model_validate(c) for c in items],
        total=total,
    )


@router.post(
    "",
    response_model=CityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание нового города",
    description="Добавляет новый город в систему (доступно только super_admin)",
    dependencies=[Depends(get_current_superadmin)],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        409: {"model": ErrorResponse, "description": "City with this name or alias already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_city(
    payload: CityCreate,
    service: CityService = Depends(get_city_service),
) -> CityResponse:
    city = await service.create_city(payload)
    return CityResponse.model_validate(city)


@router.get(
    "/{city_id}",
    response_model=CityResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение города по ID",
    dependencies=[Depends(get_current_superadmin)],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "City not found"},
    },
)
async def get_city(
    city_id: int,
    service: CityService = Depends(get_city_service),
) -> CityResponse:
    city = await service.get_city(city_id)
    return CityResponse.model_validate(city)


@router.patch(
    "/{city_id}",
    response_model=CityResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновление города",
    dependencies=[Depends(get_current_superadmin)],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "City not found"},
        409: {"model": ErrorResponse, "description": "Conflict with existing name or alias"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_city(
    city_id: int,
    payload: CityUpdate,
    service: CityService = Depends(get_city_service),
) -> CityResponse:
    city = await service.update_city(city_id, payload)
    return CityResponse.model_validate(city)


@router.delete(
    "/{city_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление города",
    dependencies=[Depends(get_current_superadmin)],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "City not found"},
    },
)
async def delete_city(
    city_id: int,
    service: CityService = Depends(get_city_service),
) -> None:
    await service.delete_city(city_id)
