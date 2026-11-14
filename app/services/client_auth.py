import json
import logging
import secrets
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.cruds.client_user import ClientUserCrud
from app.cruds.city import CityCrud
from app.db.models.client_user import ClientUser
from app.exceptions.auth import (
    AccountInactiveError,
    AuthenticationRequiredError,
    InvalidOTPError,
    SessionExpiredError,
    TooManyAuthRequests,
)
from app.exceptions.codes import ErrorCode
from app.exceptions.http import NotFoundError
from app.schemas.client_auth import RequestCodeResponse
from app.services.client_session import ClientSessionService
from app.services.telegram import TelegramService

logger = logging.getLogger("app.client_auth")


class ClientAuthService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.crud = ClientUserCrud(session)
        self._redis = redis
        self.session_service = ClientSessionService(redis)
        self.telegram_service = TelegramService(redis)

    async def _check_rate_limit(self, phone: str) -> None:
        key = f"{settings.REDIS_RATE_LIMIT_PREFIX}:client:{phone}"
        attempts = await self._redis.incr(key)

        if attempts == 1:
            await self._redis.expire(key, settings.RATE_LIMIT_RESET_TIME)

        if attempts > 5:
            raise TooManyAuthRequests()

    async def request_code(self, phone: str) -> RequestCodeResponse:
        await self._check_rate_limit(phone)

        # 4-digit OTP
        code = str(secrets.randbelow(9000) + 1000)
        auth_token = secrets.token_hex(8)

        otp_payload = json.dumps(
            {
                "code": code,
                "auth_token": auth_token,
                "attempts": 0,
            }
        )
        link_payload = json.dumps(
            {
                "phone": phone,
                "code": code,
            }
        )

        otp_key = f"{settings.REDIS_CLIENT_OTP_PREFIX}{phone}"
        link_key = f"{settings.REDIS_CLIENT_AUTH_LINK_PREFIX}{auth_token}"

        await self._redis.setex(otp_key, settings.OTP_TTL, otp_payload)
        await self._redis.setex(link_key, settings.OTP_TTL, link_payload)

        bot_url = f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={auth_token}"

        logger.info(
            "[CLIENT-OTP] Phone: %s | Code: %s | Bot Link: %s",
            phone,
            code,
            bot_url,
        )

        dev_code = code if settings_is_local_or_dev() else None

        return RequestCodeResponse(
            bot_url=bot_url,
            auth_token=auth_token,
            dev_code=dev_code,
        )

    async def verify_code(
        self,
        phone: str,
        code: str,
        ip: str | None,
        user_agent: str | None,
    ) -> tuple[str, ClientUser]:
        otp_key = f"{settings.REDIS_CLIENT_OTP_PREFIX}{phone}"
        raw = await self._redis.get(otp_key)

        if not raw:
            raise InvalidOTPError()

        data = json.loads(raw)
        attempts = data.get("attempts", 0)

        if attempts >= 3:
            await self._redis.delete(otp_key)
            if "auth_token" in data:
                await self._redis.delete(
                    f"{settings.REDIS_CLIENT_AUTH_LINK_PREFIX}{data['auth_token']}"
                )
            raise TooManyAuthRequests()

        if data["code"] != code:
            data["attempts"] = attempts + 1
            ttl = await self._redis.ttl(otp_key)
            if ttl > 0:
                await self._redis.setex(otp_key, ttl, json.dumps(data))
            raise InvalidOTPError()

        # Delete OTP after successful verification
        await self._redis.delete(otp_key)
        if "auth_token" in data:
            await self._redis.delete(
                f"{settings.REDIS_CLIENT_AUTH_LINK_PREFIX}{data['auth_token']}"
            )

        # Upsert user
        user = await self.crud.get_by_phone(phone)
        if not user:
            user = await self.crud.create(
                phone=phone,
                name=None,
                is_active=True,
            )
            await self.session.commit()
        else:
            if not user.is_active:
                raise AccountInactiveError()

        session_id = await self.session_service.create_session(
            user.id,
            ip,
            user_agent,
        )

        return session_id, user

    async def get_current_client_user(self, session_id: str) -> ClientUser:
        data = await self.session_service.get_session(session_id)
        if not data:
            raise AuthenticationRequiredError()

        user = await self.crud.get_by_id(data["user_id"])
        if not user:
            await self.session_service.invalidate_session(session_id)
            raise SessionExpiredError()

        if not user.is_active:
            await self.session_service.invalidate_session(session_id)
            raise AccountInactiveError()

        return user

    async def update_current_user(
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

    async def logout(self, session_id: str) -> None:
        await self.session_service.invalidate_session(session_id)


def settings_is_local_or_dev() -> bool:
    import os
    env = (os.getenv("APP_ENV") or "local").lower()
    return env in ("local", "dev")
