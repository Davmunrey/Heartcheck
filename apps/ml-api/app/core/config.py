from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HEARTSCAN_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )

    api_key: str = "dev-key-change-me"
    cors_origins: str = "*"
    max_upload_bytes: int = 10 * 1024 * 1024
    pipeline_version: str = "0.1.0"
    model_path: str | None = None
    request_timeout_seconds: float = 120.0
    assumed_strip_duration_sec: float = 6.0
    use_assumed_time_axis_for_bpm: bool = True

    database_url: str = "sqlite:///./data/heartscan.db"
    jwt_secret_key: str = "dev-jwt-secret-change-in-production-min-32-chars!!"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080
    allow_legacy_api_key: bool = True
    beta_daily_analysis_quota: int = 100
    sentry_dsn: str | None = None

    # Clerk (optional — when set, Bearer tokens are verified via JWKS first)
    clerk_jwks_url: str | None = None
    clerk_issuer: str | None = None
    # Shared secret between Next.js and ML API (X-Internal-Token)
    ml_internal_token: str | None = None
    # Email/password auth routes (tests / local dev). Disable in Clerk-only prod.
    auth_legacy_enabled: bool = True

    # Hard-case storage (plan v2 §G2). Disabled until legal review approves the
    # consent UX. When enabled, images flagged for review are encrypted with
    # AES-GCM using HEARTSCAN_HARD_CASE_KEY (32 bytes, base64) and stored under
    # HEARTSCAN_HARD_CASE_DIR. See docs/PRIVACY.md.
    hard_case_storage_enabled: bool = False
    hard_case_storage_dir: str = "./data/hard_cases"
    hard_case_key: str | None = None  # base64 32-byte key


@lru_cache
def get_settings() -> Settings:
    return Settings()
