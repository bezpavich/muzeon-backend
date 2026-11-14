from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


class ClientFavoriteMuseum(Base):
    __tablename__ = "client_favorite_museum"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    client_user_id: Mapped[int] = mapped_column(
        ForeignKey("client_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    museum_id: Mapped[int] = mapped_column(
        ForeignKey("museum.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    client_user = relationship("ClientUser", back_populates="favorite_museums")
    museum = relationship("Museum")

    __table_args__ = (
        UniqueConstraint("client_user_id", "museum_id", name="uq_client_user_museum_favorite"),
    )


class ClientFavoriteEvent(Base):
    __tablename__ = "client_favorite_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    client_user = relationship("ClientUser", back_populates="favorite_events")
    event = relationship("Event")

    __table_args__ = (
        UniqueConstraint("client_user_id", "event_id", name="uq_client_user_event_favorite"),
    )
