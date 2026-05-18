#!/usr/bin/env python3
"""Export JSON Schema for AnalysisResponse (and friends) to a file.

Only imports pydantic — no FastAPI, slowapi, torch, or other heavy deps.

Usage:
    python scripts/export_openapi.py [--out PATH]

Default output: openapi.json in the repo root (next to turbo.json).
Used by: scripts/codegen.sh to regenerate packages/api-client/src/generated.ts
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.schemas.analysis import AnalysisResponse


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Export AnalysisResponse JSON Schema")
    repo_root = Path(__file__).resolve().parents[3]
    p.add_argument(
        "--out",
        default=str(repo_root / "openapi.json"),
        help="Output path for the JSON Schema",
    )
    args = p.parse_args(argv)

    schema = AnalysisResponse.model_json_schema()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schema, indent=2, ensure_ascii=False))
    print(f"AnalysisResponse JSON Schema written to {out}")


if __name__ == "__main__":
    main()
