from fastapi import APIRouter

from app.api.v1.endpoints.admin import (
    auth,
    cities as admin_cities,
    dashboard,
    events,
    museum_users,
    museums,
    session,
    tickets as admin_tickets,
    users,
)
from app.api.v1.endpoints.client import (
    auth as client_auth,
    cities as client_cities,
    events as client_events,
    favorites as client_favorites,
    health as client_health,
    me as client_me,
    museums as client_museums,
    search as client_search,
    tickets as client_tickets,
)
from app.core.config import settings

api_router = APIRouter(prefix=settings.URL_PREFIX)

api_router.include_router(client_health.router)
api_router.include_router(client_auth.router)
api_router.include_router(client_me.router)
api_router.include_router(client_cities.router)
api_router.include_router(client_museums.router)
api_router.include_router(client_events.router)
api_router.include_router(client_search.router)
api_router.include_router(client_favorites.router)
api_router.include_router(client_tickets.router)
api_router.include_router(auth.router)
api_router.include_router(admin_cities.router)
api_router.include_router(dashboard.router)
api_router.include_router(museums.router)
api_router.include_router(museum_users.router)
api_router.include_router(events.router)
api_router.include_router(admin_tickets.router)
api_router.include_router(users.router)
api_router.include_router(session.router)
