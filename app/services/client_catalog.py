from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.city import City
from app.db.models.client_favorite import ClientFavoriteEvent, ClientFavoriteMuseum
from app.db.models.event import Event, EventLocation, EventType
from app.db.models.museum import Museum
from app.enums.database import EventStatusEnum, MuseumStatusEnum
from app.exceptions.codes import ErrorCode
from app.exceptions.http import NotFoundError
from app.schemas.city import CityResponse
from app.schemas.client_catalog import (
    ClientEventItem,
    ClientGlobalSearchResponse,
    ClientMuseumDetail,
    ClientMuseumItem,
    ClientMuseumLocationItem,
)


class ClientCatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_favorite_museum_ids(self, user_id: int | None) -> set[int]:
        if not user_id:
            return set()
        stmt = select(ClientFavoriteMuseum.museum_id).where(ClientFavoriteMuseum.client_user_id == user_id)
        result = await self.session.execute(stmt)
        return set(result.scalars().all())

    async def _get_favorite_event_ids(self, user_id: int | None) -> set[int]:
        if not user_id:
            return set()
        stmt = select(ClientFavoriteEvent.event_id).where(ClientFavoriteEvent.client_user_id == user_id)
        result = await self.session.execute(stmt)
        return set(result.scalars().all())

    @staticmethod
    def _map_event(event: Event, is_favorite: bool = False) -> ClientEventItem:
        city_res = None
        if event.museum and event.museum.city:
            city_res = CityResponse.model_validate(event.museum.city)

        return ClientEventItem(
            id=event.id,
            title=event.title,
            description=event.description,
            capacity=event.capacity,
            date_start=event.date_start,
            date_end=event.date_end,
            is_recurring=event.is_recurring,
            museum_id=event.museum_id,
            museum_name=event.museum.name if event.museum else "",
            location_id=event.location_id,
            location_name=event.location.name if event.location else None,
            location_address=event.location.address if event.location else None,
            type_id=event.type_id,
            type_name=event.event_type.name if event.event_type else None,
            city=city_res,
            is_favorite=is_favorite,
        )

    @staticmethod
    def _map_museum(museum: Museum, is_favorite: bool = False) -> ClientMuseumItem:
        city_res = None
        if museum.city:
            city_res = CityResponse.model_validate(museum.city)

        return ClientMuseumItem(
            id=museum.id,
            name=museum.name,
            address=museum.address,
            phone=museum.phone,
            email=museum.email,
            city=city_res,
            is_favorite=is_favorite,
        )

    async def list_museums(
        self,
        city_id: int | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 20,
        user_id: int | None = None,
    ) -> tuple[list[ClientMuseumItem], int]:
        filters = [
            Museum.status.in_([MuseumStatusEnum.active, MuseumStatusEnum.trial])
        ]

        if city_id is not None:
            filters.append(Museum.city_id == city_id)

        if query and query.strip():
            q = f"%{query.strip().lower()}%"
            filters.append(func.lower(Museum.name).like(q))

        count_stmt = select(func.count()).select_from(Museum).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Museum)
            .options(selectinload(Museum.city))
            .where(*filters)
            .order_by(Museum.name.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        museums = result.scalars().all()

        fav_ids = await self._get_favorite_museum_ids(user_id)
        return [self._map_museum(m, is_favorite=m.id in fav_ids) for m in museums], total

    async def get_museum(
        self,
        museum_id: int,
        user_id: int | None = None,
    ) -> ClientMuseumDetail:
        stmt = (
            select(Museum)
            .options(selectinload(Museum.city), selectinload(Museum.locations))
            .where(
                Museum.id == museum_id,
                Museum.status.in_([MuseumStatusEnum.active, MuseumStatusEnum.trial]),
            )
        )
        result = await self.session.execute(stmt)
        museum = result.scalar_one_or_none()
        if not museum:
            raise NotFoundError(ErrorCode.NOT_FOUND, "Museum not found")

        city_res = None
        if museum.city:
            city_res = CityResponse.model_validate(museum.city)

        locations = [
            ClientMuseumLocationItem(
                id=loc.id,
                name=loc.name,
                description=loc.description,
                address=loc.address,
                latitude=loc.latitude,
                longitude=loc.longitude,
            )
            for loc in (museum.locations or [])
            if loc.is_active
        ]

        fav_ids = await self._get_favorite_museum_ids(user_id)
        return ClientMuseumDetail(
            id=museum.id,
            name=museum.name,
            address=museum.address,
            phone=museum.phone,
            email=museum.email,
            city=city_res,
            is_favorite=museum.id in fav_ids,
            locations=locations,
        )

    async def list_events(
        self,
        city_id: int | None = None,
        museum_id: int | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 20,
        user_id: int | None = None,
    ) -> tuple[list[ClientEventItem], int]:
        filters = [
            Event.status == EventStatusEnum.published,
            Museum.status.in_([MuseumStatusEnum.active, MuseumStatusEnum.trial]),
        ]

        if city_id is not None:
            filters.append(Museum.city_id == city_id)

        if museum_id is not None:
            filters.append(Event.museum_id == museum_id)

        if query and query.strip():
            q = f"%{query.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Event.title).like(q),
                    func.lower(Event.description).like(q),
                )
            )

        count_stmt = (
            select(func.count())
            .select_from(Event)
            .join(Event.museum)
            .where(*filters)
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Event)
            .join(Event.museum)
            .options(
                selectinload(Event.museum).selectinload(Museum.city),
                selectinload(Event.location),
                selectinload(Event.event_type),
            )
            .where(*filters)
            .order_by(Event.date_start.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        events = result.scalars().all()

        fav_ids = await self._get_favorite_event_ids(user_id)
        return [self._map_event(e, is_favorite=e.id in fav_ids) for e in events], total

    async def get_event(
        self,
        event_id: int,
        user_id: int | None = None,
    ) -> ClientEventItem:
        stmt = (
            select(Event)
            .join(Event.museum)
            .options(
                selectinload(Event.museum).selectinload(Museum.city),
                selectinload(Event.location),
                selectinload(Event.event_type),
            )
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

        fav_ids = await self._get_favorite_event_ids(user_id)
        return self._map_event(event, is_favorite=event.id in fav_ids)

    async def global_search(
        self,
        query: str,
        city_id: int | None = None,
        limit: int = 10,
        user_id: int | None = None,
    ) -> ClientGlobalSearchResponse:
        museums, _ = await self.list_museums(
            city_id=city_id,
            query=query,
            offset=0,
            limit=limit,
            user_id=user_id,
        )
        events, _ = await self.list_events(
            city_id=city_id,
            query=query,
            offset=0,
            limit=limit,
            user_id=user_id,
        )
        return ClientGlobalSearchResponse(
            museums=museums,
            events=events,
        )
