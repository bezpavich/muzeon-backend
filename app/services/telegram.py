import json
import logging
import httpx
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger("app.telegram")


class TelegramService:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.bot_username = settings.TELEGRAM_BOT_USERNAME

    async def send_message(self, chat_id: int | str, text: str) -> bool:
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN is not configured. Message not sent: %s", text)
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    return True
                logger.error("Failed to send telegram message: %s", response.text)
                return False
        except Exception as e:
            logger.error("Telegram send error: %s", e)
            return False

    async def process_update(self, update: dict) -> None:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return

        chat = message.get("chat", {})
        chat_id = chat.get("id")
        text = (message.get("text") or "").strip()

        if not chat_id:
            return

        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            if len(parts) > 1:
                auth_token = parts[1].strip()
                link_key = f"{settings.REDIS_CLIENT_AUTH_LINK_PREFIX}{auth_token}"
                raw = await self._redis.get(link_key)
                if raw:
                    data = json.loads(raw)
                    code = data.get("code")
                    reply = (
                        f"🔐 Ваш код для входа в MUZEON: <b>{code}</b>\n\n"
                        f"Код действует 5 минут. Введите его на странице входа в приложении."
                    )
                    await self.send_message(chat_id, reply)
                    return

                await self.send_message(
                    chat_id,
                    "⚠️ Срок действия кода истёк или ссылка недействительна. Пожалуйста, запросите код повторно в приложении."
                )
                return

            await self.send_message(
                chat_id,
                "👋 Привет! Это бот авторизации <b>MUZEON</b>.\n\n"
                "Чтобы получить код для входа, нажмите «Получить код в Telegram» на странице входа в приложении."
            )
