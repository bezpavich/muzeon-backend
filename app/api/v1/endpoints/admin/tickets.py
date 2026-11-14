from fastapi import APIRouter, Depends, status

from app.api.dependencies import EventManager, EventReader, get_ticket_service
from app.db.models.admin_user import AdminUser
from app.exceptions.schemas import ErrorResponse
from app.schemas.ticket import (
    TicketTypeCreate,
    TicketTypeListResponse,
    TicketTypeResponse,
    TicketTypeUpdate,
    TicketValidateRequest,
    TicketValidateResponse,
)
from app.services.ticket import TicketService

router = APIRouter(tags=["Admin Tickets"])


@router.post(
    "/events/{event_id}/tickets",
    response_model=TicketTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать категорию билета для события",
    description="Добавляет категорию билета (тариф) с указанием стоимости и лимита мест",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Event not found"},
    },
)
async def create_ticket_type(
    event_id: int,
    data: TicketTypeCreate,
    current_user: EventManager,
    service: TicketService = Depends(get_ticket_service),
) -> TicketTypeResponse:
    return await service.create_ticket_type(
        event_id=event_id,
        data=data,
        current_user=current_user,
    )


@router.get(
    "/events/{event_id}/tickets",
    response_model=TicketTypeListResponse,
    status_code=status.HTTP_200_OK,
    summary="Список категорий билетов события",
    description="Возвращает все настроенные категории билетов события для админки",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Event not found"},
    },
)
async def list_ticket_types(
    event_id: int,
    current_user: EventReader,
    service: TicketService = Depends(get_ticket_service),
) -> TicketTypeListResponse:
    items, total = await service.list_ticket_types(
        event_id=event_id,
        current_user=current_user,
    )
    return TicketTypeListResponse(items=items, total=total)


@router.patch(
    "/tickets/types/{ticket_type_id}",
    response_model=TicketTypeResponse,
    status_code=status.HTTP_200_OK,
    summary="Изменить категорию билета",
    description="Обновляет название, стоимость, общее количество или статус активности",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Ticket type not found"},
    },
)
async def update_ticket_type(
    ticket_type_id: int,
    data: TicketTypeUpdate,
    current_user: EventManager,
    service: TicketService = Depends(get_ticket_service),
) -> TicketTypeResponse:
    return await service.update_ticket_type(
        ticket_type_id=ticket_type_id,
        data=data,
        current_user=current_user,
    )


@router.delete(
    "/tickets/types/{ticket_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить или деактивировать категорию билета",
    description="Удаляет категорию, если билеты ещё не проданы, либо деактивирует её",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Ticket type not found"},
    },
)
async def delete_ticket_type(
    ticket_type_id: int,
    current_user: EventManager,
    service: TicketService = Depends(get_ticket_service),
) -> None:
    await service.delete_ticket_type(
        ticket_type_id=ticket_type_id,
        current_user=current_user,
    )


@router.post(
    "/tickets/validate",
    response_model=TicketValidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Валидация / гашение билета на входе (сканирование QR)",
    description="Проверяет валидность билета по QR-коду или номеру. Если билет действителен, гасит его (статус used)",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    },
)
async def validate_ticket(
    data: TicketValidateRequest,
    current_user: EventManager,
    service: TicketService = Depends(get_ticket_service),
) -> TicketValidateResponse:
    return await service.validate_ticket(
        code=data.code,
        current_user=current_user,
    )
