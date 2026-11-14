from fastapi import APIRouter, Depends, Request, Response, status

from app.api.dependencies import (
    get_client_auth_service,
    get_telegram_service,
)
from app.core.config import settings
from app.exceptions.schemas import ErrorResponse
from app.schemas.client_auth import (
    RequestCodeRequest,
    RequestCodeResponse,
    VerifyCodeRequest,
)
from app.schemas.client_user import ClientUserResponse
from app.services.client_auth import ClientAuthService
from app.services.telegram import TelegramService

router = APIRouter(prefix="/client/auth", tags=["Client Auth"])


@router.post(
    "/request-code",
    response_model=RequestCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Запрос одноразового кода для входа в PWA",
    description="Генерирует 4-значный OTP код и ссылку на Telegram-бота",
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        429: {"model": ErrorResponse, "description": "Too many requests"},
    },
)
async def request_code(
    payload: RequestCodeRequest,
    service: ClientAuthService = Depends(get_client_auth_service),
) -> RequestCodeResponse:
    return await service.request_code(payload.phone)


@router.post(
    "/verify-code",
    response_model=ClientUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Проверка кода и вход в PWA",
    description="Проверяет OTP код, регистрирует нового пользователя или находит существующего, создает сессию в Redis и ставит HttpOnly cookie",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid OTP code"},
        403: {"model": ErrorResponse, "description": "Account is inactive"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        429: {"model": ErrorResponse, "description": "Too many requests"},
    },
)
async def verify_code(
    payload: VerifyCodeRequest,
    request: Request,
    response: Response,
    service: ClientAuthService = Depends(get_client_auth_service),
) -> ClientUserResponse:
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    session_id, user = await service.verify_code(
        phone=payload.phone,
        code=payload.code,
        ip=ip,
        user_agent=user_agent,
    )

    response.set_cookie(
        key=settings.CLIENT_SESSION_COOKIE,
        value=session_id,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.SESSION_TTL,
    )

    return ClientUserResponse.model_validate(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выход из профиля PWA",
    description="Удаляет сессию пользователя из Redis и очищает сессионную куку",
)
async def logout(
    request: Request,
    response: Response,
    service: ClientAuthService = Depends(get_client_auth_service),
) -> Response:
    session_id = request.cookies.get(settings.CLIENT_SESSION_COOKIE)
    if not session_id:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_id = auth_header.split(" ", 1)[1].strip()

    if session_id:
        await service.logout(session_id)

    response.delete_cookie(
        key=settings.CLIENT_SESSION_COOKIE,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/telegram/webhook",
    status_code=status.HTTP_200_OK,
    summary="Telegram Bot Webhook",
    description="Обрабатывает входящие обновления от Telegram Bot API (например, нажатие /start)",
)
async def telegram_webhook(
    update: dict,
    service: TelegramService = Depends(get_telegram_service),
) -> dict:
    await service.process_update(update)
    return {"ok": True}
