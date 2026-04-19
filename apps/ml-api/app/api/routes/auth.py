from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.limiter import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.schemas.user import TokenResponse, UserCreate, UserPublic
from app.services.usage_service import get_user_by_email

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, body: UserCreate, db: Session = Depends(get_db)) -> UserPublic:
    if get_user_by_email(db, body.email.lower()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "EMAIL_EXISTS", "message": "Email already registered"},
        )
    u = User(email=body.email.lower(), hashed_password=hash_password(body.password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return UserPublic.model_validate(u)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
def login(request: Request, body: UserCreate, db: Session = Depends(get_db)) -> TokenResponse:
    from app.core.config import get_settings

    u = get_user_by_email(db, body.email.lower())
    if not u or not verify_password(body.password, u.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
        )
    settings = get_settings()
    token = create_access_token(str(u.id), u.id, u.email, settings)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserPublic)
def me(current: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    return UserPublic.model_validate(current)
