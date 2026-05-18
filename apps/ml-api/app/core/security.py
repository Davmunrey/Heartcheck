from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import PyJWTError
from passlib.context import CryptContext

from app.core.config import Settings, get_settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_access_token(subject: str, user_id: int, email: str, settings: Settings | None = None) -> str:
    s = settings or get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=s.jwt_expire_minutes)
    payload = {"sub": subject, "uid": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)


def decode_token(token: str, settings: Settings | None = None) -> dict:
    s = settings or get_settings()
    try:
        return jwt.decode(token, s.jwt_secret_key, algorithms=[s.jwt_algorithm])
    except PyJWTError as e:
        raise ValueError("invalid_token") from e
