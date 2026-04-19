from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UsageDaily, User


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def get_today_count(db: Session, company_id: str) -> int:
    day = utc_today()
    row = db.execute(
        select(UsageDaily).where(UsageDaily.company_id == company_id, UsageDaily.day == day)
    ).scalar_one_or_none()
    return int(row.count) if row else 0


def increment_today(db: Session, company_id: str) -> None:
    day = utc_today()
    row = db.execute(
        select(UsageDaily).where(UsageDaily.company_id == company_id, UsageDaily.day == day)
    ).scalar_one_or_none()
    if row:
        row.count = int(row.count) + 1
    else:
        db.add(UsageDaily(company_id=company_id, day=day, count=1))
    db.commit()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)
