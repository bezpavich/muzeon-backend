from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    get_client_favorite_service,
    get_current_client_user,
)
from app.db.models.client_user import ClientUser
from app.exceptions.schemas import ErrorResponse
from app.schemas.client_catalog import (
    ClientEventListResponse,
    ClientMuseumListResponse,
)
from app.schemas.client_favorite import (
    ClientFavoriteIdsResponse,
    ClientFavoritesResponse,
    ClientFavoriteStatus,
)
from app.services.client_favorite import ClientFavoriteService

router = APIRouter(prefix="/client/favorites", tags=["Client Favorites"])


@router.get(
    "",
    response_model=ClientFavoritesResponse,
    status_code=status.HTTP_200_OK,
    summary="Все избранные объекты (вкладка Избранное)",
    description="Возвращает списки избранных музеев и событий текущего пользователя для отображения во вкладке 'Избранное'",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def get_all_favorites(
    current_user: ClientUser = Depends(get_current_client_user),
    service: ClientFavoriteService = Depends(get_client_favorite_service),
) -> ClientFavoritesResponse:
    return await service.get_all_favorites(user_id=current_user.id)


@router.get(
    "/ids",
    response_model=ClientFavoriteIdsResponse,
    status_code=status.HTTP_200_OK,
    summary="Список ID всех избранных объектов",
    description="Возвращает массивы ID избранных музеев и событий для быстрого сопоставления на клиенте",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def get_favorite_ids(
    current_user: ClientUser = Depends(get_current_client_user),
    service: ClientFavoriteService = Depends(get_client_favorite_service),
) -> ClientFavoriteIdsResponse:
    return await service.get_favorite_ids(user_id=current_user.id)


@router.get(
    "/museums",
    response_model=ClientMuseumListResponse,
    status_code=status.HTTP_200_OK,
    summary="Избранные музеи (с пагинацией)",
    description="Возвращает постраничный список избранных музеев пользователя",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def list_favorite_museums(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: ClientUser = Depends(get_current_client_user),
    service: ClientFavoriteService = Depends(get_client_favorite_service),
) -> ClientMuseumListResponse:
    items, total = await service.get_favorite_museums(
        user_id=current_user.id,
        offset=offset,
        limit=limit,
    )
    return ClientMuseumListResponse(items=items, total=total)


@router.get(
    "/events",
    response_model=ClientEventListResponse,
    status_code=status.HTTP_200_OK,
    summary="Избранные события (с пагинацией)",
    description="Возвращает постраничный список избранных событий пользователя",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def list_favorite_events(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: ClientUser = Depends(get_current_client_user),
    service: ClientFavoriteService = Depends(get_client_favorite_service),
) -> ClientEventListResponse:
    items, total = await service.get_favorite_events(
        user_id=current_user.id,
        offset=offset,
        limit=limit,
    )
    return ClientEventListResponse(items=items, total=total)


@router.post(
    "/museums/{museum_id}",
    response_model=ClientFavoriteStatus,
    status_code=status.HTTP_200_OK,
    summary="Поставить / снять лайк музея",
    description="Переключает статус избранного: если лайка нет — ставит (true), если есть — снимает (false)",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Museum not found"},
    },
)
async def toggle_museum_favorite(
    museum_id: int,
    current_user: ClientUser = Depends(get_current_client_user),
    service: ClientFavoriteService = Depends(get_client_favorite_service),
) -> ClientFavoriteStatus:
    is_fav = await service.toggle_museum_favorite(user_id=current_user.id, museum_id=museum_id)
    return ClientFavoriteStatus(is_favorite=is_fav)


@router.post(
    "/events/{event_id}",
    response_model=ClientFavoriteStatus,
    status_code=status.HTTP_200_OK,
    summary="Поставить / снять лайк события",
    description="Переключает статус избранного: если лайка нет — ставит (true), если есть — снимает (false)",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Event not found"},
    },
)
async def toggle_event_favorite(
    event_id: int,
    current_user: ClientUser = Depends(get_current_client_user),
    service: ClientFavoriteService = Depends(get_client_favorite_service),
) -> ClientFavoriteStatus:
    is_fav = await service.toggle_event_favorite(user_id=current_user.id, event_id=event_id)
    return ClientFavoriteStatus(is_favorite=is_fav)
