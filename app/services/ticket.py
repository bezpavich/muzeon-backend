import io
import secrets
from datetime import datetime, timezone

import segno
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.admin_user import AdminUser
from app.db.models.client_user import ClientUser
from app.db.models.event import Event, EventLocation
from app.db.models.museum import Museum
from app.db.models.ticket import ClientTicket, TicketType
from app.enums.database import EventStatusEnum, MuseumStatusEnum, TicketStatusEnum, UserRoleEnum
from app.exceptions.codes import ErrorCode
from app.exceptions.http import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from app.schemas.ticket import (
    ClientBuyTicketRequest,
    ClientTicketEventInfo,
    ClientTicketItem,
    ClientTicketQRResponse,
    ClientTicketTypeInfo,
    TicketTypeCreate,
    TicketTypeResponse,
    TicketTypeUpdate,
    TicketValidateResponse,
)
from app.services.tenant import check_museum_access


def generate_ticket_number() -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = secrets.token_hex(3).upper()
    return f"TICK-{now_str}-{random_part}"


def generate_qr_data(ticket_number: str) -> str:
    token = secrets.token_urlsafe(16)
    return f"MUZEON:{ticket_number}:{token}"


def render_qr_svg(code: str) -> str:
    qr = segno.make_qr(code)
    out = io.BytesIO()
    qr.save(out, kind="svg", scale=8, border=2)
    return out.getvalue().decode("utf-8")


def render_qr_data_uri(code: str) -> str:
    qr = segno.make_qr(code)
    return qr.svg_data_uri(scale=8, border=2)


def render_qr_bytes(code: str) -> bytes:
    qr = segno.make_qr(code)
    out = io.BytesIO()
    qr.save(out, kind="svg", scale=8, border=2)
    return out.getvalue()


class TicketService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ==========================================================
    # Helper mappers
    # ==========================================================

    @staticmethod
    def _map_ticket_type(t: TicketType) -> TicketTypeResponse:
        return TicketTypeResponse(
            id=t.id,
            event_id=t.event_id,
            museum_id=t.museum_id,
            name=t.name,
            description=t.description,
            price=t.price,
            total_quantity=t.total_quantity,
            available_quantity=t.available_quantity,
            is_active=t.is_active,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )

    @staticmethod
    def _map_client_ticket(t: ClientTicket) -> ClientTicketItem:
        city_name = None
        if t.event and t.event.museum and t.event.museum.city:
            city_name = t.event.museum.city.name

        location_name = t.event.location.name if t.event and t.event.location else None
        location_address = t.event.location.address if t.event and t.event.location else None

        event_info = ClientTicketEventInfo(
            id=t.event.id,
            title=t.event.title,
            description=t.event.description,
            date_start=t.event.date_start,
            date_end=t.event.date_end,
            is_recurring=t.event.is_recurring,
            museum_id=t.event.museum_id,
            museum_name=t.event.museum.name if t.event.museum else "",
            museum_address=t.event.museum.address if t.event.museum else "",
            city_name=city_name,
            location_name=location_name,
            location_address=location_address,
        )

        ticket_type_info = None
        if t.ticket_type:
            ticket_type_info = ClientTicketTypeInfo(
                id=t.ticket_type.id,
                name=t.ticket_type.name,
                description=t.ticket_type.description,
            )

        return ClientTicketItem(
            id=t.id,
            ticket_number=t.ticket_number,
            status=t.status,
            price=t.price,
            created_at=t.created_at,
            ticket_type=ticket_type_info,
            event=event_info,
            qr_code_data=t.qr_code_data,
            qr_code_data_uri=render_qr_data_uri(t.qr_code_data),
            qr_image_url=f"/api/v1/client/tickets/{t.id}/qr.svg",
        )

    # ==========================================================
    # Admin Ticket Types Management
    # ==========================================================

    async def create_ticket_type(
        self,
        event_id: int,
        data: TicketTypeCreate,
        current_user: AdminUser,
    ) -> TicketTypeResponse:
        stmt = select(Event).where(Event.id == event_id)
        result = await self.session.execute(stmt)
        event = result.scalar_one_or_none()
        if not event:
            raise NotFoundError(ErrorCode.NOT_FOUND, "Event not found")

        check_museum_access(current_user, event.museum_id)

        ticket_type = TicketType(
            name=data.name,
            description=data.description,
            price=data.price,
            total_quantity=data.total_quantity,
            available_quantity=data.total_quantity,
            is_active=data.is_active,
            event_id=event.id,
            museum_id=event.museum_id,
        )
        self.session.add(ticket_type)
        await self.session.commit()
        await self.session.refresh(ticket_type)
        return self._map_ticket_type(ticket_type)

    async def list_ticket_types(
        self,
        event_id: int,
        current_user: AdminUser,
    ) -> tuple[list[TicketTypeResponse], int]:
        stmt = select(Event).where(Event.id == event_id)
        result = await self.session.execute(stmt)
        event = result.scalar_one_or_none()
        if not event:
            raise NotFoundError(ErrorCode.NOT_FOUND, "Event not found")

        check_museum_access(current_user, event.museum_id)

        count_stmt = (
            select(func.count())
            .select_from(TicketType)
            .where(TicketType.event_id == event_id)
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        items_stmt = (
            select(TicketType)
            .where(TicketType.event_id == event_id)
            .order_by(TicketType.price.asc(), TicketType.name.asc())
        )
        items = (await self.session.execute(items_stmt)).scalars().all()
        return [self._map_ticket_type(t) for t in items], total

    async def update_ticket_type(
        self,
        ticket_type_id: int,
        data: TicketTypeUpdate,
        current_user: AdminUser,
    ) -> TicketTypeResponse:
        stmt = select(TicketType).where(TicketType.id == ticket_type_id)
        result = await self.session.execute(stmt)
        ticket_type = result.scalar_one_or_none()
        if not ticket_type:
            raise NotFoundError(ErrorCode.NOT_FOUND, "Ticket type not found")

        check_museum_access(current_user, ticket_type.museum_id)

        if data.name is not None:
            ticket_type.name = data.name
        if data.description is not None:
            ticket_type.description = data.description
        if data.price is not None:
            ticket_type.price = data.price
        if data.is_active is not None:
            ticket_type.is_active = data.is_active

        if data.total_quantity is not None:
            diff = data.total_quantity - ticket_type.total_quantity
            new_available = ticket_type.available_quantity + diff
            if new_available < 0:
                raise BadRequestError(
                    ErrorCode.INVALID_VALUE,
                    "Total quantity cannot be less than already sold tickets",
                )
            ticket_type.total_quantity = data.total_quantity
            ticket_type.available_quantity = new_available

        await self.session.commit()
        await self.session.refresh(ticket_type)
        return self._map_ticket_type(ticket_type)

    async def delete_ticket_type(
        self,
        ticket_type_id: int,
        current_user: AdminUser,
    ) -> None:
        stmt = select(TicketType).where(TicketType.id == ticket_type_id)
        result = await self.session.execute(stmt)
        ticket_type = result.scalar_one_or_none()
        if not ticket_type:
            raise NotFoundError(ErrorCode.NOT_FOUND, "Ticket type not found")

        check_museum_access(current_user, ticket_type.museum_id)

        # Check if tickets have been issued
        count_stmt = (
            select(func.count())
            .select_from(ClientTicket)
            .where(ClientTicket.ticket_type_id == ticket_type_id)
        )
        sold_count = (await self.session.execute(count_stmt)).scalar_one()
        if sold_count > 0:
            # If tickets already bought, deactivate instead of deleting
            ticket_type.is_active = False
            await self.session.commit()
            return

        await self.session.delete(ticket_type)
        await self.session.commit()

    # ==========================================================
    # Admin Ticket Validation (At the entrance)
    # ==========================================================

    async def validate_ticket(
        self,
        code: str,
        current_user: AdminUser,
    ) -> TicketValidateResponse:
        cleaned_code = code.strip()

        stmt = (
            select(ClientTicket)
            .options(
                selectinload(ClientTicket.event),
                selectinload(ClientTicket.ticket_type),
                selectinload(ClientTicket.client_user),
            )
            .where(
                or_(
                    ClientTicket.qr_code_data == cleaned_code,
                    ClientTicket.ticket_number == cleaned_code,
                )
            )
        )
        result = await self.session.execute(stmt)
        ticket = result.scalar_one_or_none()

        if not ticket:
            return TicketValidateResponse(
                valid=False,
                details="Билет с таким номером или QR-кодом не найден в системе",
            )

        if current_user.role != UserRoleEnum.super_admin and current_user.museum_id != ticket.museum_id:
            raise PermissionDeniedError()

        visitor_name = ticket.client_user.name if ticket.client_user else None
        visitor_phone = ticket.client_user.phone if ticket.client_user else None
        event_title = ticket.event.title if ticket.event else None
        type_name = ticket.ticket_type.name if ticket.ticket_type else None

        if ticket.status == TicketStatusEnum.used:
            return TicketValidateResponse(
                valid=False,
                ticket_id=ticket.id,
                ticket_number=ticket.ticket_number,
                status=ticket.status,
                event_title=event_title,
                ticket_type_name=type_name,
                visitor_name=visitor_name,
                visitor_phone=visitor_phone,
                details="Билет уже был использован ранее",
            )

        if ticket.status == TicketStatusEnum.canceled:
            return TicketValidateResponse(
                valid=False,
                ticket_id=ticket.id,
                ticket_number=ticket.ticket_number,
                status=ticket.status,
                event_title=event_title,
                ticket_type_name=type_name,
                visitor_name=visitor_name,
                visitor_phone=visitor_phone,
                details="Билет аннулирован",
            )

        if ticket.status == TicketStatusEnum.expired:
            return TicketValidateResponse(
                valid=False,
                ticket_id=ticket.id,
                ticket_number=ticket.ticket_number,
                status=ticket.status,
                event_title=event_title,
                ticket_type_name=type_name,
                visitor_name=visitor_name,
                visitor_phone=visitor_phone,
                details="Срок действия билета истёк",
            )

        # Mark ticket as used
        ticket.status = TicketStatusEnum.used
        await self.session.commit()

        return TicketValidateResponse(
            valid=True,
            ticket_id=ticket.id,
            ticket_number=ticket.ticket_number,
            status=TicketStatusEnum.used,
            event_title=event_title,
            ticket_type_name=type_name,
            visitor_name=visitor_name,
            visitor_phone=visitor_phone,
            details="Билет действителен. Проход разрешён!",
        )

    # ==========================================================
    # Client API (PWA)
    # ==========================================================

    async def list_event_ticket_types(self, event_id: int) -> list[TicketTypeResponse]:
        stmt = (
            select(TicketType)
            .join(TicketType.event)
            .join(Event.museum)
            .where(
                TicketType.event_id == event_id,
                TicketType.is_active.is_(True),
                Event.status == EventStatusEnum.published,
                Museum.status.in_([MuseumStatusEnum.active, MuseumStatusEnum.trial]),
            )
            .order_by(TicketType.price.asc(), TicketType.name.asc())
        )
        result = await self.session.execute(stmt)
        types = result.scalars().all()
        return [self._map_ticket_type(t) for t in types]

    async def buy_tickets(
        self,
        user_id: int,
        event_id: int,
        data: ClientBuyTicketRequest,
    ) -> list[ClientTicketItem]:
        # Lock and check ticket type
        stmt = (
            select(TicketType)
            .join(TicketType.event)
            .join(Event.museum)
            .where(
                TicketType.id == data.ticket_type_id,
                TicketType.event_id == event_id,
                TicketType.is_active.is_(True),
                Event.status == EventStatusEnum.published,
                Museum.status.in_([MuseumStatusEnum.active, MuseumStatusEnum.trial]),
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        ticket_type = result.scalar_one_or_none()

        if not ticket_type:
            raise NotFoundError(ErrorCode.NOT_FOUND, "Ticket type not found or unavailable")

        if ticket_type.available_quantity < data.quantity:
            raise BadRequestError(
                ErrorCode.INVALID_VALUE,
                f"Недостаточно доступных билетов (осталось {ticket_type.available_quantity})",
            )

        ticket_type.available_quantity -= data.quantity

        created_tickets: list[ClientTicket] = []
        for _ in range(data.quantity):
            t_number = generate_ticket_number()
            qr_data = generate_qr_data(t_number)
            ticket = ClientTicket(
                ticket_number=t_number,
                qr_code_data=qr_data,
                status=TicketStatusEnum.valid,
                price=ticket_type.price,
                client_user_id=user_id,
                event_id=event_id,
                ticket_type_id=ticket_type.id,
                museum_id=ticket_type.museum_id,
            )
            self.session.add(ticket)
            created_tickets.append(ticket)

        await self.session.commit()

        # Load relationships for response
        ticket_ids = [t.id for t in created_tickets]
        load_stmt = (
            select(ClientTicket)
            .options(
                selectinload(ClientTicket.ticket_type),
                selectinload(ClientTicket.event).selectinload(Event.museum).selectinload(Museum.city),
                selectinload(ClientTicket.event).selectinload(Event.location),
            )
            .where(ClientTicket.id.in_(ticket_ids))
            .order_by(ClientTicket.id.asc())
        )
        loaded = (await self.session.execute(load_stmt)).scalars().all()
        return [self._map_client_ticket(t) for t in loaded]

    async def list_user_tickets(
        self,
        user_id: int,
        status_filter: str = "upcoming",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ClientTicketItem], int]:
        now = datetime.now(timezone.utc)
        effective_event_date = func.coalesce(Event.date_end, Event.date_start)

        filters = [ClientTicket.client_user_id == user_id]

        if status_filter == "upcoming":
            filters.append(ClientTicket.status == TicketStatusEnum.valid)
            filters.append(effective_event_date >= now)
        elif status_filter == "past":
            filters.append(
                or_(
                    ClientTicket.status.in_([TicketStatusEnum.used, TicketStatusEnum.canceled, TicketStatusEnum.expired]),
                    effective_event_date < now,
                )
            )

        count_stmt = (
            select(func.count())
            .select_from(ClientTicket)
            .join(ClientTicket.event)
            .where(*filters)
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        order = Event.date_start.asc() if status_filter == "upcoming" else ClientTicket.created_at.desc()

        stmt = (
            select(ClientTicket)
            .join(ClientTicket.event)
            .options(
                selectinload(ClientTicket.ticket_type),
                selectinload(ClientTicket.event).selectinload(Event.museum).selectinload(Museum.city),
                selectinload(ClientTicket.event).selectinload(Event.location),
            )
            .where(*filters)
            .order_by(order)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        tickets = result.scalars().all()
        return [self._map_client_ticket(t) for t in tickets], total

    async def get_ticket(
        self,
        user_id: int,
        ticket_id: int,
    ) -> ClientTicketItem:
        stmt = (
            select(ClientTicket)
            .options(
                selectinload(ClientTicket.ticket_type),
                selectinload(ClientTicket.event).selectinload(Event.museum).selectinload(Museum.city),
                selectinload(ClientTicket.event).selectinload(Event.location),
            )
            .where(
                ClientTicket.id == ticket_id,
                ClientTicket.client_user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise NotFoundError(ErrorCode.NOT_FOUND, "Ticket not found")

        return self._map_client_ticket(ticket)

    async def get_ticket_qr(
        self,
        user_id: int,
        ticket_id: int,
    ) -> ClientTicketQRResponse:
        stmt = (
            select(ClientTicket)
            .options(
                selectinload(ClientTicket.event).selectinload(Event.museum),
                selectinload(ClientTicket.client_user),
            )
            .where(
                ClientTicket.id == ticket_id,
                ClientTicket.client_user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise NotFoundError(ErrorCode.NOT_FOUND, "Ticket not found")

        qr_svg = render_qr_svg(ticket.qr_code_data)
        qr_data_uri = render_qr_data_uri(ticket.qr_code_data)

        return ClientTicketQRResponse(
            ticket_id=ticket.id,
            ticket_number=ticket.ticket_number,
            status=ticket.status,
            qr_code_data=ticket.qr_code_data,
            qr_code_svg=qr_svg,
            qr_code_data_uri=qr_data_uri,
            event_title=ticket.event.title,
            museum_name=ticket.event.museum.name if ticket.event.museum else "",
            museum_address=ticket.event.museum.address if ticket.event.museum else "",
            date_start=ticket.event.date_start,
            visitor_name=ticket.client_user.name if ticket.client_user else None,
            visitor_phone=ticket.client_user.phone if ticket.client_user else None,
        )

    async def get_ticket_qr_svg_bytes(
        self,
        user_id: int,
        ticket_id: int,
    ) -> bytes:
        stmt = select(ClientTicket).where(
            ClientTicket.id == ticket_id,
            ClientTicket.client_user_id == user_id,
        )
        result = await self.session.execute(stmt)
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise NotFoundError(ErrorCode.NOT_FOUND, "Ticket not found")

        return render_qr_bytes(ticket.qr_code_data)
