import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import analyze, auth, education, feedback, health, meta, reports
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.limiter import limiter
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services import inference as inf

logger = get_logger(__name__)


def _resolve_web_public_dir() -> Path:
    """Serve SaaS landing from repo `web_public/` (dev) or image `/app/web_public` (Docker)."""
    here = Path(__file__).resolve()
    for d in [here.parent.parent, *here.parents]:
        cand = d / "web_public"
        if (cand / "index.html").is_file():
            return cand
    docker = Path("/app/web_public")
    if (docker / "index.html").is_file():
        return docker
    return Path.cwd() / "web_public"


def _ensure_sqlite_parent(db_url: str) -> None:
    if not db_url.startswith("sqlite:///"):
        return
    path = db_url.replace("sqlite:///", "", 1)
    if not path or path == ":memory:" or path.startswith("memory"):
        return
    Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


_INSECURE_JWT_DEFAULTS = {
    "dev-jwt-secret-change-in-production-min-32-chars!!",
    "change-me-in-production-min-32-chars-long!!",
    "replace-with-long-random-secret-min-32-chars",
}
_INSECURE_API_KEY_DEFAULTS = {"dev-key-change-me", "change-me-in-production", ""}


def _refuse_insecure_production_defaults(settings) -> None:
    """Fail fast if production runs with placeholder secrets or open CORS.

    Catches the most common deploy-time mistake (forgetting to override the
    ``HEARTSCAN_*`` env vars baked into ``apps/ml-api/.env.example``).
    """
    env = os.getenv("HEARTSCAN_ENV", "development").lower()
    if env != "production":
        return
    problems: list[str] = []
    if settings.jwt_secret_key in _INSECURE_JWT_DEFAULTS or len(settings.jwt_secret_key) < 32:
        problems.append("HEARTSCAN_JWT_SECRET_KEY is a default/short value")
    if settings.allow_legacy_api_key and settings.api_key in _INSECURE_API_KEY_DEFAULTS:
        problems.append("HEARTSCAN_API_KEY is a default value while legacy auth is enabled")
    if settings.cors_origins.strip() == "*":
        problems.append("HEARTSCAN_CORS_ORIGINS='*' is forbidden in production")
    if problems:
        raise RuntimeError(
            "Refusing to start in production with insecure defaults: " + "; ".join(problems)
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    _refuse_insecure_production_defaults(settings)
    _ensure_sqlite_parent(settings.database_url)
    import app.db.models  # noqa: F401
    from app.db.session import Base, get_engine

    Base.metadata.create_all(bind=get_engine())
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=0.1,
            environment=os.getenv("HEARTSCAN_ENV", "development"),
        )
    if settings.model_path:
        p = Path(settings.model_path)
        if p.is_file():
            inf.load_model(str(p))
            logger.info("model_loaded", path=str(p))
        else:
            logger.info("model_path_missing", path=str(p))
    else:
        logger.info("no_model_path", message="Using heuristic classifier until weights are configured")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="HeartScan API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins == ["*"] or not origins:
        # The CORS spec forbids `Access-Control-Allow-Origin: *` together with
        # `Access-Control-Allow-Credentials: true`; browsers refuse credentialed
        # requests in that combination. Keep wildcard only for non-credentialed
        # local dev; production should override `HEARTSCAN_CORS_ORIGINS`.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health.router)
    app.include_router(meta.router)
    if settings.auth_legacy_enabled:
        app.include_router(auth.router)
    app.include_router(analyze.router)
    app.include_router(education.router)
    app.include_router(reports.router)
    app.include_router(feedback.router)

    web_root = _resolve_web_public_dir()
    if (web_root / "static").is_dir():
        app.mount("/static", StaticFiles(directory=web_root / "static"), name="static")
    if (web_root / "legal").is_dir():
        app.mount("/legal", StaticFiles(directory=web_root / "legal"), name="legal")

    @app.get("/", include_in_schema=False)
    def spa_landing() -> FileResponse:
        return FileResponse(web_root / "index.html")

    @app.get("/app", include_in_schema=False)
    def spa_web_app() -> FileResponse:
        return FileResponse(web_root / "app.html")

    @app.get("/faq.html", include_in_schema=False)
    def faq_page() -> FileResponse:
        return FileResponse(web_root / "faq.html")

    @app.exception_handler(Exception)
    async def global_exc(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", "")
        logger.exception("unhandled", request_id=rid, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": rid,
            },
        )

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
