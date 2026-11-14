from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_current_client_user, get_ticket_service
from app.db.models.client_user import ClientUser
from app.exceptions.schemas import ErrorResponse
from app.schemas.ticket import (
    ClientBuyTicketRequest,
    ClientTicketItem,
    ClientTicketListResponse,
    ClientTicketQRResponse,
    TicketTypeResponse,
)
from app.services.ticket import TicketService

router = APIRouter(prefix="/client", tags=["Client Tickets"])


@router.get(
    "/events/{event_id}/tickets",
    response_model=list[TicketTypeResponse],
    status_code=status.HTTP_200_OK,
    summary="Доступные тарифы билетов на событие",
    description="Возвращает доступные для покупки категории билетов (стоимость, название, условия)",
    responses={
        404: {"model": ErrorResponse, "description": "Event not found"},
    },
)
async def list_event_tickets(
    event_id: int,
    service: TicketService = Depends(get_ticket_service),
) -> list[TicketTypeResponse]:
    return await service.list_event_ticket_types(event_id)


@router.post(
    "/events/{event_id}/tickets/buy",
    response_model=list[ClientTicketItem],
    status_code=status.HTTP_201_CREATED,
    summary="Покупка / бронирование билетов",
    description="Создаёт купленные билеты для текущего авторизованного пользователя и списывает остаток",
    responses={
        400: {"model": ErrorResponse, "description": "Insufficient tickets available"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Event or ticket type not found"},
    },
)
async def buy_tickets(
    event_id: int,
    data: ClientBuyTicketRequest,
    current_user: ClientUser = Depends(get_current_client_user),
    service: TicketService = Depends(get_ticket_service),
) -> list[ClientTicketItem]:
    return await service.buy_tickets(
        user_id=current_user.id,
        event_id=event_id,
        data=data,
    )


@router.get(
    "/tickets",
    response_model=ClientTicketListResponse,
    status_code=status.HTTP_200_OK,
    summary="Экран 'Мои билеты'",
    description="Возвращает список билетов пользователя с фильтрацией на предстоящие (upcoming) и прошедшие (past)",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def list_my_tickets(
    filter: str = Query("upcoming", pattern="^(upcoming|past|all)$", description="Фильтр: upcoming (предстоящие), past (прошедшие/использованные), all (все)"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: ClientUser = Depends(get_current_client_user),
    service: TicketService = Depends(get_ticket_service),
) -> ClientTicketListResponse:
    items, total = await service.list_user_tickets(
        user_id=current_user.id,
        status_filter=filter,
        offset=offset,
        limit=limit,
    )
    return ClientTicketListResponse(items=items, total=total)


@router.get(
    "/tickets/{ticket_id}",
    response_model=ClientTicketItem,
    status_code=status.HTTP_200_OK,
    summary="Детальная информация о билете",
    description="Возвращает полную карточку билета пользователя",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Ticket not found"},
    },
)
async def get_my_ticket(
    ticket_id: int,
    current_user: ClientUser = Depends(get_current_client_user),
    service: TicketService = Depends(get_ticket_service),
) -> ClientTicketItem:
    return await service.get_ticket(
        user_id=current_user.id,
        ticket_id=ticket_id,
    )


@router.get(
    "/tickets/{ticket_id}/qr",
    response_model=ClientTicketQRResponse,
    status_code=status.HTTP_200_OK,
    summary="Открыть QR-код билета",
    description="Возвращает данные QR-кода, векторный SVG и data-uri для немедленного отображения в модальном окне или экране QR",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Ticket not found"},
    },
)
async def get_ticket_qr(
    ticket_id: int,
    current_user: ClientUser = Depends(get_current_client_user),
    service: TicketService = Depends(get_ticket_service),
) -> ClientTicketQRResponse:
    return await service.get_ticket_qr(
        user_id=current_user.id,
        ticket_id=ticket_id,
    )


@router.get(
    "/tickets/{ticket_id}/qr.svg",
    status_code=status.HTTP_200_OK,
    summary="SVG изображение QR-кода",
    description="Отдаёт векторный файл QR-кода билета (Content-Type: image/svg+xml) для использования напрямую в теге <img>",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Ticket not found"},
    },
)
async def get_ticket_qr_image(
    ticket_id: int,
    current_user: ClientUser = Depends(get_current_client_user),
    service: TicketService = Depends(get_ticket_service),
) -> Response:
    svg_bytes = await service.get_ticket_qr_svg_bytes(
        user_id=current_user.id,
        ticket_id=ticket_id,
    )
    return Response(content=svg_bytes, media_type="image/svg+xml")
