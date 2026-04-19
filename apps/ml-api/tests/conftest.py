import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _test_env_and_db() -> None:
    os.environ.setdefault("HEARTSCAN_API_KEY", "test-key")
    os.environ.setdefault("HEARTSCAN_ALLOW_LEGACY_API_KEY", "true")
    os.environ.setdefault("HEARTSCAN_JWT_SECRET_KEY", "pytest-jwt-secret-key-minimum-32-characters-long")
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["HEARTSCAN_DATABASE_URL"] = f"sqlite:///{path}"
    # Tests use legacy JWT + API key. Must override .env/.env.local (pydantic merges files + env).
    os.environ["HEARTSCAN_CLERK_JWKS_URL"] = ""
    os.environ["HEARTSCAN_CLERK_ISSUER"] = ""

    from app.core.config import get_settings
    from app.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()

    import app.db.models  # noqa: F401
    from app.db.session import Base, get_engine as ge

    Base.metadata.create_all(bind=ge())


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)
