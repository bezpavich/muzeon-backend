from fastapi import APIRouter, status

router = APIRouter(prefix="/client", tags=["Client System"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check клиентского API",
    description="Проверка доступности и работоспособности клиентского сервиса PWA",
)
@router.get(
    "/healthcheck",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def client_health() -> dict:
    return {"status": "ok"}
