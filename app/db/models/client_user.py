from sqlalchemy import BigInteger, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.models.base import Base
from app.db.mixin import DateMixin


class ClientUser(Base, DateMixin):

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    phone: Mapped[str] = mapped_column(String(length=20), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(length=150), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    city_id: Mapped[int | None] = mapped_column(ForeignKey("city.id"), nullable=True)

    city = relationship("City", back_populates="users")
    favorite_museums = relationship(
        "ClientFavoriteMuseum",
        back_populates="client_user",
        cascade="all, delete-orphan",
    )
    favorite_events = relationship(
        "ClientFavoriteEvent",
        back_populates="client_user",
        cascade="all, delete-orphan",
    )
    tickets = relationship(
        "ClientTicket",
        back_populates="client_user",
        cascade="all, delete-orphan",
    )
