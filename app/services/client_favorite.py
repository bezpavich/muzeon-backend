from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.client_favorite import ClientFavoriteEvent, ClientFavoriteMuseum
from app.db.models.event import Event
from app.db.models.museum import Museum
from app.enums.database import EventStatusEnum, MuseumStatusEnum
from app.exceptions.codes import ErrorCode
from app.exceptions.http import NotFoundError
from app.schemas.client_catalog import ClientEventItem, ClientMuseumItem
from app.schemas.client_favorite import (
    ClientFavoriteIdsResponse,
    ClientFavoritesResponse,
)
from app.services.client_catalog import ClientCatalogService


class ClientFavoriteService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.catalog_service = ClientCatalogService(session)

    async def _verify_museum_exists(self, museum_id: int) -> Museum:
        stmt = select(Museum).where(
            Museum.id == museum_id,
            Museum.status.in_([MuseumStatusEnum.active, MuseumStatusEnum.trial]),
        )
        result = await self.session.execute(stmt)
        museum = result.scalar_one_or_none()
        if not museum:
            raise NotFoundError(ErrorCode.NOT_FOUND, "Museum not found")
        return museum

    async def _verify_event_exists(self, event_id: int) -> Event:
        stmt = (
            select(Event)
            .join(Event.museum)
            .where(
                Event.id == event_id,
                Event.status == EventStatusEnum.published,
                Museum.status.in_([MuseumStatusEnum.active, MuseumStatusEnum.trial]),
            )
        )
        result = await self.session.execute(stmt)
        event = result.scalar_one_or_none()
        if not event:
            raise NotFoundError(ErrorCode.NOT_FOUND, "Event not found")
        return event

    async def add_museum_favorite(self, user_id: int, museum_id: int) -> bool:
        await self._verify_museum_exists(museum_id)
        stmt = select(ClientFavoriteMuseum).where(
            ClientFavoriteMuseum.client_user_id == user_id,
            ClientFavoriteMuseum.museum_id == museum_id,
        )
        result = await self.session.execute(stmt)
        fav = result.scalar_one_or_none()
        if not fav:
            fav = ClientFavoriteMuseum(
                client_user_id=user_id,
                museum_id=museum_id,
            )
            self.session.add(fav)
            await self.session.commit()
        return True

    async def remove_museum_favorite(self, user_id: int, museum_id: int) -> bool:
        stmt = select(ClientFavoriteMuseum).where(
            ClientFavoriteMuseum.client_user_id == user_id,
            ClientFavoriteMuseum.museum_id == museum_id,
        )
        result = await self.session.execute(stmt)
        fav = result.scalar_one_or_none()
        if fav:
            await self.session.delete(fav)
            await self.session.commit()
        return False

    async def toggle_museum_favorite(self, user_id: int, museum_id: int) -> bool:
        await self._verify_museum_exists(museum_id)
        stmt = select(ClientFavoriteMuseum).where(
            ClientFavoriteMuseum.client_user_id == user_id,
            ClientFavoriteMuseum.museum_id == museum_id,
        )
        result = await self.session.execute(stmt)
        fav = result.scalar_one_or_none()
        if fav:
            await self.session.delete(fav)
            await self.session.commit()
            return False
        else:
            fav = ClientFavoriteMuseum(
                client_user_id=user_id,
                museum_id=museum_id,
            )
            self.session.add(fav)
            await self.session.commit()
            return True

    async def add_event_favorite(self, user_id: int, event_id: int) -> bool:
        await self._verify_event_exists(event_id)
        stmt = select(ClientFavoriteEvent).where(
            ClientFavoriteEvent.client_user_id == user_id,
            ClientFavoriteEvent.event_id == event_id,
        )
        result = await self.session.execute(stmt)
        fav = result.scalar_one_or_none()
        if not fav:
            fav = ClientFavoriteEvent(
                client_user_id=user_id,
                event_id=event_id,
            )
            self.session.add(fav)
            await self.session.commit()
        return True

    async def remove_event_favorite(self, user_id: int, event_id: int) -> bool:
        stmt = select(ClientFavoriteEvent).where(
            ClientFavoriteEvent.client_user_id == user_id,
            ClientFavoriteEvent.event_id == event_id,
        )
        result = await self.session.execute(stmt)
        fav = result.scalar_one_or_none()
        if fav:
            await self.session.delete(fav)
            await self.session.commit()
        return False

    async def toggle_event_favorite(self, user_id: int, event_id: int) -> bool:
        await self._verify_event_exists(event_id)
        stmt = select(ClientFavoriteEvent).where(
            ClientFavoriteEvent.client_user_id == user_id,
            ClientFavoriteEvent.event_id == event_id,
        )
        result = await self.session.execute(stmt)
        fav = result.scalar_one_or_none()
        if fav:
            await self.session.delete(fav)
            await self.session.commit()
            return False
        else:
            fav = ClientFavoriteEvent(
                client_user_id=user_id,
                event_id=event_id,
            )
            self.session.add(fav)
            await self.session.commit()
            return True

    async def get_favorite_ids(self, user_id: int) -> ClientFavoriteIdsResponse:
        museum_stmt = select(ClientFavoriteMuseum.museum_id).where(
            ClientFavoriteMuseum.client_user_id == user_id
        )
        museum_ids = (await self.session.execute(museum_stmt)).scalars().all()

        event_stmt = select(ClientFavoriteEvent.event_id).where(
            ClientFavoriteEvent.client_user_id == user_id
        )
        event_ids = (await self.session.execute(event_stmt)).scalars().all()

        return ClientFavoriteIdsResponse(
            museum_ids=list(museum_ids),
            event_ids=list(event_ids),
        )

    async def get_all_favorites(self, user_id: int) -> ClientFavoritesResponse:
        museums, _ = await self.get_favorite_museums(user_id=user_id, offset=0, limit=100)
        events, _ = await self.get_favorite_events(user_id=user_id, offset=0, limit=100)
        return ClientFavoritesResponse(
            museums=museums,
            events=events,
        )

    async def get_favorite_museums(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ClientMuseumItem], int]:
        filters = [
            ClientFavoriteMuseum.client_user_id == user_id,
            Museum.status.in_([MuseumStatusEnum.active, MuseumStatusEnum.trial]),
        ]

        count_stmt = (
            select(func.count())
            .select_from(ClientFavoriteMuseum)
            .join(Museum, ClientFavoriteMuseum.museum_id == Museum.id)
            .where(*filters)
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Museum)
            .join(ClientFavoriteMuseum, ClientFavoriteMuseum.museum_id == Museum.id)
            .options(selectinload(Museum.city))
            .where(*filters)
            .order_by(ClientFavoriteMuseum.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        museums = result.scalars().all()

        items = [self.catalog_service._map_museum(m, is_favorite=True) for m in museums]
        return items, total

    async def get_favorite_events(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ClientEventItem], int]:
        filters = [
            ClientFavoriteEvent.client_user_id == user_id,
            Event.status == EventStatusEnum.published,
            Museum.status.in_([MuseumStatusEnum.active, MuseumStatusEnum.trial]),
        ]

        count_stmt = (
            select(func.count())
            .select_from(ClientFavoriteEvent)
            .join(Event, ClientFavoriteEvent.event_id == Event.id)
            .join(Event.museum)
            .where(*filters)
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Event)
            .join(ClientFavoriteEvent, ClientFavoriteEvent.event_id == Event.id)
            .join(Event.museum)
            .options(
                selectinload(Event.museum).selectinload(Museum.city),
                selectinload(Event.location),
                selectinload(Event.event_type),
            )
            .where(*filters)
            .order_by(ClientFavoriteEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        events = result.scalars().all()

        items = [self.catalog_service._map_event(e, is_favorite=True) for e in events]
        return items, total
