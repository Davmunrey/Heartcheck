"""Education topics (localized YAML)."""

from pathlib import Path

import yaml
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/v1", tags=["education"])

_KNOWLEDGE = Path(__file__).resolve().parent.parent.parent / "knowledge"


def _load_topics(locale: str) -> list[dict]:
    fname = "ecg_topics_es.yaml" if locale.startswith("es") else "ecg_topics_en.yaml"
    p = _KNOWLEDGE / fname
    if not p.is_file():
        p = _KNOWLEDGE / "ecg_topics_en.yaml"
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("topics", [])


@router.get("/education/topics")
def list_topics(locale: str = Query("en", description="Locale code, e.g. en or es")) -> dict:
    topics = _load_topics(locale)
    return {"topics": topics}
