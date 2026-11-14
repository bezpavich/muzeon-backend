from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.models.client_user import ClientUser
from app.cruds.base import Base


class ClientUserCrud(Base[ClientUser]):
    model = ClientUser

    def _with_city(self, stmt):
        return stmt.options(selectinload(ClientUser.city))

    async def get_by_id(self, _id: int) -> ClientUser | None:
        result = await self.session.execute(
            self._with_city(select(ClientUser).where(ClientUser.id == _id))
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> ClientUser | None:
        result = await self.session.execute(
            self._with_city(select(ClientUser).where(ClientUser.phone == phone))
        )
        return result.scalar_one_or_none()
