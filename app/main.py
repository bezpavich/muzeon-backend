from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import close_redis, init_redis
from app.db.session import close_db
from app.exceptions import app_exception_handler, validation_exception_handler
from app.exceptions.base import AppException
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.request_id import RequestIDMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    yield
    await close_redis()
    await close_db()


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
        title="MUZEON API",
        version=settings.VERSION,
        openapi_url=f"{settings.URL_PREFIX}/openapi.json",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_exception_handler(
        AppException,
        app_exception_handler,
    )
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )

    # Cached OpenAPI schemas
    cached_schemas: dict[str, dict] = {}

    @app.get(f"{settings.URL_PREFIX}/admin/openapi.json", include_in_schema=False)
    async def get_admin_openapi():
        if "admin" not in cached_schemas:
            admin_routes = [
                r
                for r in app.routes
                if getattr(r, "path", "").startswith(settings.URL_PREFIX)
                and not getattr(r, "path", "").startswith(f"{settings.URL_PREFIX}/client")
                and getattr(r, "include_in_schema", True)
            ]
            cached_schemas["admin"] = get_openapi(
                title="MUZEON Admin API",
                version=settings.VERSION,
                description="API панели управления администратора MUZEON",
                routes=admin_routes,
            )
        return JSONResponse(cached_schemas["admin"])

    @app.get(f"{settings.URL_PREFIX}/client/openapi.json", include_in_schema=False)
    async def get_client_openapi():
        if "client" not in cached_schemas:
            client_routes = [
                r
                for r in app.routes
                if getattr(r, "path", "").startswith(f"{settings.URL_PREFIX}/client")
                and getattr(r, "include_in_schema", True)
            ]
            cached_schemas["client"] = get_openapi(
                title="MUZEON Client API",
                version=settings.VERSION,
                description="API клиентского приложения (PWA для посетителей) MUZEON",
                routes=client_routes,
            )
        return JSONResponse(cached_schemas["client"])

    @app.get(f"{settings.URL_PREFIX}/docs", include_in_schema=False)
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8"/>
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>MUZEON API Docs</title>
          <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
          <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png" />
          <style>
            .swagger-ui .topbar .download-url-wrapper input[type=text],
            .swagger-ui .topbar .download-url-wrapper .download-url-button {{
              display: none !important;
            }}
            .swagger-ui .topbar .download-url-wrapper {{
              display: flex;
              align-items: center;
              gap: 8px;
            }}
            .swagger-ui .topbar .download-url-wrapper select {{
              min-width: 300px;
              font-size: 14px;
              padding: 6px 12px;
              border-radius: 4px;
              border: 1px solid #3b4151;
              background-color: #fff;
              color: #3b4151;
              cursor: pointer;
            }}
          </style>
        </head>
        <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
        <script>
        window.onload = function() {{
          window.ui = SwaggerUIBundle({{
            urls: [
              {{ url: '{settings.URL_PREFIX}/admin/openapi.json', name: 'Admin API' }},
              {{ url: '{settings.URL_PREFIX}/client/openapi.json', name: 'Client API' }}
            ],
            'urls.primaryName': 'Admin API',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
              SwaggerUIBundle.presets.apis,
              SwaggerUIStandalonePreset
            ],
            plugins: [
              SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: 'StandaloneLayout'
          }});
        }};
        </script>
        </body>
        </html>
        """
        from fastapi.responses import HTMLResponse
        return HTMLResponse(html)

    @app.get(f"{settings.URL_PREFIX}/redoc", include_in_schema=False)
    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc_html():
        return get_redoc_html(
            openapi_url=f"{settings.URL_PREFIX}/openapi.json",
            title="MUZEON API ReDoc",
        )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
