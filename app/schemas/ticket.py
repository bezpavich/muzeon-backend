from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.enums.database import TicketStatusEnum


# ==========================================
# Ticket Types (Admin & Catalog)
# ==========================================

class TicketTypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="Название категории билета (напр. 'Входной', 'Льготный')")
    description: str | None = Field(None, description="Описание условий тарифа")
    price: float = Field(0.0, ge=0.0, description="Стоимость билета в рублях (0 = бесплатно)")
    total_quantity: int = Field(100, ge=1, description="Общее доступное количество билетов")
    is_active: bool = Field(True, description="Доступен ли билет для покупки")


class TicketTypeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = None
    price: float | None = Field(None, ge=0.0)
    total_quantity: int | None = Field(None, ge=1)
    is_active: bool | None = None


class TicketTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    museum_id: int
    name: str
    description: str | None = None
    price: float
    total_quantity: int
    available_quantity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TicketTypeListResponse(BaseModel):
    items: list[TicketTypeResponse]
    total: int


# ==========================================
# Client Tickets (PWA)
# ==========================================

class ClientBuyTicketRequest(BaseModel):
    ticket_type_id: int = Field(..., description="ID категории билета")
    quantity: int = Field(1, ge=1, le=10, description="Количество билетов (от 1 до 10)")


class ClientTicketTypeInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class ClientTicketEventInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    date_start: datetime
    date_end: datetime | None = None
    is_recurring: bool
    museum_id: int
    museum_name: str
    museum_address: str
    city_name: str | None = None
    location_name: str | None = None
    location_address: str | None = None


class ClientTicketItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    status: TicketStatusEnum
    price: float
    created_at: datetime
    ticket_type: ClientTicketTypeInfo | None = None
    event: ClientTicketEventInfo
    qr_code_data: str
    qr_code_data_uri: str
    qr_image_url: str


class ClientTicketListResponse(BaseModel):
    items: list[ClientTicketItem]
    total: int


class ClientTicketQRResponse(BaseModel):
    ticket_id: int
    ticket_number: str
    status: TicketStatusEnum
    qr_code_data: str
    qr_code_svg: str
    qr_code_data_uri: str
    event_title: str
    museum_name: str
    museum_address: str
    date_start: datetime
    visitor_name: str | None = None
    visitor_phone: str | None = None


# ==========================================
# Admin Ticket Validation (Scan at entrance)
# ==========================================

class TicketValidateRequest(BaseModel):
    code: str = Field(..., description="QR-код (qr_code_data) или номер билета (ticket_number)")


class TicketValidateResponse(BaseModel):
    valid: bool
    ticket_id: int | None = None
    ticket_number: str | None = None
    status: TicketStatusEnum | None = None
    event_title: str | None = None
    ticket_type_name: str | None = None
    visitor_name: str | None = None
    visitor_phone: str | None = None
    details: str
