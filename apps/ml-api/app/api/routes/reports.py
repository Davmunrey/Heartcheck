"""Server-side PDF report from analysis JSON (no raw image)."""

from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse

from app.api.deps import AnalyzeAuth, require_analyze_auth
from app.schemas.analysis import ReportPdfRequest

router = APIRouter(prefix="/api/v1", tags=["reports"])


@router.post(
    "/reports/pdf",
    response_class=StreamingResponse,
    summary="Generate PDF report",
    description="Builds a structured PDF from a prior analysis payload. Requires Bearer JWT or legacy API key when enabled.",
)
def build_pdf(
    body: ReportPdfRequest,
    _auth: Annotated[AnalyzeAuth, Depends(require_analyze_auth)],
) -> Response:
    # Lazy import: reportlab is heavy; keep API/landing startup fast.
    from app.services.pdf_report import build_analysis_pdf_bytes

    pdf_bytes = build_analysis_pdf_bytes(
        body.analysis,
        locale=body.locale,
        app_version=body.app_version,
    )
    buf = BytesIO(pdf_bytes)
    rid = body.analysis.request_id.replace("/", "_")[:32]
    filename = f"heartscan_report_{rid}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
