from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds.city import CityCrud
from app.db.models.city import City
from app.exceptions.codes import ErrorCode
from app.exceptions.http import ConflictError, NotFoundError
from app.schemas.city import CityCreate, CityUpdate
from app.services.utils import slugify


class CityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.crud = CityCrud(session)

    async def list_cities(
        self,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[City], int]:
        return await self.crud.list_cities(
            is_active=is_active,
            offset=offset,
            limit=limit,
        )

    async def get_city(self, city_id: int) -> City:
        city = await self.crud.get_by_id(city_id)
        if not city:
            raise NotFoundError(ErrorCode.NOT_FOUND, "City not found")
        return city

    async def create_city(self, data: CityCreate) -> City:
        name = data.name.strip()
        alias = (data.alias or slugify(name)).strip().lower()

        existing_name = await self.crud.get_by_name(name)
        if existing_name:
            raise ConflictError(ErrorCode.CONFLICT, "City with this name already exists")

        existing_alias = await self.crud.get_by_alias(alias)
        if existing_alias:
            raise ConflictError(ErrorCode.CONFLICT, "City with this alias already exists")

        city = await self.crud.create(
            name=name,
            alias=alias,
            is_active=data.is_active,
        )
        await self.session.commit()
        return city

    async def update_city(self, city_id: int, data: CityUpdate) -> City:
        city = await self.get_city(city_id)
        update_dict = {}

        if data.name is not None:
            name = data.name.strip()
            existing = await self.crud.get_by_name(name)
            if existing and existing.id != city_id:
                raise ConflictError(ErrorCode.CONFLICT, "City with this name already exists")
            update_dict["name"] = name
            if data.alias is None:
                update_dict["alias"] = slugify(name)

        if data.alias is not None:
            alias = data.alias.strip().lower()
            existing = await self.crud.get_by_alias(alias)
            if existing and existing.id != city_id:
                raise ConflictError(ErrorCode.CONFLICT, "City with this alias already exists")
            update_dict["alias"] = alias

        if data.is_active is not None:
            update_dict["is_active"] = data.is_active

        if update_dict:
            city = await self.crud.update(city, **update_dict)
            await self.session.commit()

        return city

    async def delete_city(self, city_id: int) -> None:
        city = await self.get_city(city_id)
        await self.crud.delete(city)
        await self.session.commit()
