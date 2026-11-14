from sqlalchemy import func, select
from app.cruds.base import Base
from app.db.models.city import City


class CityCrud(Base[City]):
    model = City

    async def get_by_name(self, name: str) -> City | None:
        result = await self.session.execute(
            select(City).where(func.lower(City.name) == name.strip().lower())
        )
        return result.scalar_one_or_none()

    async def get_by_alias(self, alias: str) -> City | None:
        result = await self.session.execute(
            select(City).where(City.alias == alias.strip().lower())
        )
        return result.scalar_one_or_none()

    async def list_cities(
        self,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[City], int]:
        stmt = select(City)
        count_stmt = select(func.count()).select_from(City)

        if is_active is not None:
            stmt = stmt.where(City.is_active == is_active)
            count_stmt = count_stmt.where(City.is_active == is_active)

        stmt = stmt.order_by(City.name.asc()).offset(offset).limit(limit)

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
