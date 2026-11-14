from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.mixin import DateMixin
from app.db.models.base import Base
from app.enums.database import TicketStatusEnum


class TicketType(Base, DateMixin):
    __tablename__ = "ticket_type"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_quantity: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    available_quantity: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    event_id: Mapped[int] = mapped_column(
        ForeignKey("event.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    museum_id: Mapped[int] = mapped_column(
        ForeignKey("museum.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event = relationship("Event", back_populates="ticket_types")
    museum = relationship("Museum")
    tickets = relationship("ClientTicket", back_populates="ticket_type")


class ClientTicket(Base, DateMixin):
    __tablename__ = "client_ticket"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticket_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    qr_code_data: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[TicketStatusEnum] = mapped_column(
        Enum(TicketStatusEnum),
        default=TicketStatusEnum.valid,
        nullable=False,
        index=True,
    )
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    client_user_id: Mapped[int] = mapped_column(
        ForeignKey("client_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("event.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticket_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("ticket_type.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    museum_id: Mapped[int] = mapped_column(
        ForeignKey("museum.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client_user = relationship("ClientUser", back_populates="tickets")
    event = relationship("Event")
    ticket_type = relationship("TicketType", back_populates="tickets")
    museum = relationship("Museum")
