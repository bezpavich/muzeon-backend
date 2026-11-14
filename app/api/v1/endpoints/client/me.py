from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_client_user_service, get_current_client_user
from app.db.models.client_user import ClientUser
from app.exceptions.schemas import ErrorResponse
from app.schemas.client_user import ClientUserResponse, ClientUserUpdate
from app.services.client_user import ClientUserService

router = APIRouter(prefix="/client/me", tags=["Client Profile"])


@router.get(
    "",
    response_model=ClientUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение профиля текущего пользователя PWA",
    description="Возвращает информацию о текущем авторизованном пользователе",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Account is inactive"},
    },
)
async def get_me(
    current_user: ClientUser = Depends(get_current_client_user),
) -> ClientUserResponse:
    return ClientUserResponse.model_validate(current_user)


@router.patch(
    "",
    response_model=ClientUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновление профиля текущего пользователя PWA",
    description="Обновляет имя или выбранный город (city_id) текущего пользователя",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Account is inactive"},
        404: {"model": ErrorResponse, "description": "City not found or inactive"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_me(
    payload: ClientUserUpdate,
    current_user: ClientUser = Depends(get_current_client_user),
    service: ClientUserService = Depends(get_client_user_service),
) -> ClientUserResponse:
    updated_user = await service.update_me(
        user=current_user,
        name=payload.name,
        city_id=payload.city_id,
    )
    return ClientUserResponse.model_validate(updated_user)
