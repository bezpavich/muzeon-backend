from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds.city import CityCrud
from app.cruds.client_user import ClientUserCrud
from app.db.models.client_user import ClientUser
from app.exceptions.codes import ErrorCode
from app.exceptions.http import NotFoundError


class ClientUserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.crud = ClientUserCrud(session)

    async def update_me(
        self,
        user: ClientUser,
        name: str | None = None,
        city_id: int | None = None,
    ) -> ClientUser:
        update_data = {}
        if name is not None:
            update_data["name"] = name.strip() or None

        if city_id is not None:
            city_crud = CityCrud(self.session)
            city = await city_crud.get_by_id(city_id)
            if not city or not city.is_active:
                raise NotFoundError(ErrorCode.NOT_FOUND, "City not found or inactive")
            update_data["city_id"] = city_id

        if update_data:
            user = await self.crud.update(user, **update_data)
            await self.session.commit()

        refreshed = await self.crud.get_by_id(user.id)
        return refreshed or user
