"""Professional PDF layout for analysis reports (ReportLab platypus)."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.analysis import AnalysisResponse


def _t(locale: str) -> dict[str, str]:
    lc = (locale or "en")[:2].lower()
    if lc == "es":
        return {
            "title": "Informe de análisis Axis",
            "subtitle": (
                "Software educativo de bienestar digital. No sustituye un electrocardiograma clínico "
                "ni la valoración médica."
            ),
            "summary": "Resumen",
            "metrics": "Métricas clave",
            "interpretation": "Interpretación",
            "technical": "Trazabilidad técnica",
            "limitations": "Limitaciones y cobertura",
            "request_id": "ID de solicitud",
            "generated": "Generado (UTC)",
            "app": "Versión de app",
            "bpm": "Frecuencia (BPM, orientativa)",
            "confidence": "Confianza del modelo",
            "rhythm": "Regularidad del ritmo",
            "class_lbl": "Clasificación educativa",
            "quality": "Calidad de extracción",
            "pipeline": "Versión del pipeline",
            "model": "Versión del modelo",
            "basis": "Base BPM",
            "topics": "Temas educativos sugeridos",
            "findings": "Hallazgos documentados en esta versión",
            "non_reportable": "Motivo de no informe",
            "disclaimer_heading": "Aviso legal",
        }
    return {
        "title": "Axis Analysis Report",
        "subtitle": (
            "Educational wellbeing software. Does not replace a clinical ECG or professional "
            "medical assessment."
        ),
        "summary": "Summary",
        "metrics": "Key metrics",
        "interpretation": "Interpretation",
        "technical": "Technical traceability",
        "limitations": "Limitations and coverage",
        "request_id": "Request ID",
        "generated": "Generated (UTC)",
        "app": "App version",
        "bpm": "Heart rate (BPM, indicative)",
        "confidence": "Model confidence",
        "rhythm": "Rhythm regularity",
        "class_lbl": "Educational class",
        "quality": "Extraction quality",
        "pipeline": "Pipeline version",
        "model": "Model version",
        "basis": "BPM basis",
        "topics": "Suggested education topics",
        "findings": "Documented findings in this release",
        "non_reportable": "Non-reportable reason",
        "disclaimer_heading": "Disclaimer",
    }


def _status_color(status: str) -> colors.Color:
    return {
        # Axis clinical status tints (ok / warn / crit).
        "green": colors.HexColor("#E2F4EC"),
        "yellow": colors.HexColor("#FAEFD2"),
        "red": colors.HexColor("#FBE3E4"),
    }.get(status, colors.HexColor("#E9EDF4"))


def build_analysis_pdf_bytes(
    analysis: AnalysisResponse,
    *,
    locale: str = "en",
    app_version: str = "0.1.0",
) -> bytes:
    """Return PDF bytes for streaming."""
    labels = _t(locale)
    a = analysis
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="Axis Report",
        author="Axis",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleHS",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=6,
        textColor=colors.HexColor("#1B5FD9"),
    )
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.grey)
    disclaimer_style = ParagraphStyle(
        "Disc",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#46586E"),
    )

    story: list = []
    story.append(Paragraph(f"<b>{escape(labels['title'])}</b>", title_style))
    story.append(Paragraph(escape(labels["subtitle"]), body))
    story.append(Spacer(1, 0.35 * cm))

    gen_ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")
    meta_rows = [
        [labels["request_id"], a.request_id],
        [labels["generated"], gen_ts],
        [labels["app"], app_version],
    ]
    meta_table = Table(meta_rows, colWidths=[4.2 * cm, 12 * cm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 0.4 * cm))

    # Status banner row
    status_bg = _status_color(a.status)
    status_tbl = Table(
        [[Paragraph(f"<b>{escape(labels['summary'])}</b>: {escape(a.status.upper())}", body)]],
        colWidths=[16 * cm],
    )
    status_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), status_bg),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDBDBD")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(status_tbl)
    story.append(Spacer(1, 0.35 * cm))

    story.append(Paragraph(f"<b>{escape(labels['metrics'])}</b>", h2))
    bpm_display = "—" if a.bpm is None else f"{a.bpm:.1f}"
    metric_data = [
        [labels["class_lbl"], escape(a.class_label)],
        [labels["confidence"], f"{a.confidence_score:.2f}"],
        [labels["bpm"], bpm_display],
        [labels["rhythm"], escape(a.rhythm_regularity)],
        [labels["quality"], f"{a.extraction_quality:.2f}"],
    ]
    if a.measurement_basis:
        metric_data.append([labels["basis"], escape(a.measurement_basis)])
    m_tbl = Table(metric_data, colWidths=[5.5 * cm, 10.5 * cm])
    m_tbl.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
                ("FONT", (1, 0), (1, -1), "Helvetica", 9),
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E0E0E0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(m_tbl)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph(f"<b>{escape(labels['interpretation'])}</b>", h2))
    story.append(Paragraph(escape(a.message), body))
    story.append(Spacer(1, 0.35 * cm))

    if a.non_reportable_reason:
        story.append(Paragraph(f"<b>{escape(labels['non_reportable'])}</b>", h2))
        nrr = a.non_reportable_reason
        for k, v in nrr.items():
            story.append(Paragraph(f"<b>{escape(str(k))}</b>: {escape(str(v))}", small))
        story.append(Spacer(1, 0.25 * cm))

    if a.analysis_limit:
        story.append(Paragraph(f"<b>{escape(labels['limitations'])}</b>", h2))
        for item in a.analysis_limit:
            story.append(Paragraph(f"• {escape(item)}", body))
        story.append(Spacer(1, 0.25 * cm))

    if a.supported_findings:
        story.append(Paragraph(f"<b>{escape(labels['findings'])}</b>", h2))
        for item in a.supported_findings:
            story.append(Paragraph(f"• {escape(item)}", body))
        story.append(Spacer(1, 0.25 * cm))

    if a.education_topic_ids:
        story.append(Paragraph(f"<b>{escape(labels['topics'])}</b>", h2))
        story.append(Paragraph(escape(", ".join(a.education_topic_ids)), body))
        story.append(Spacer(1, 0.25 * cm))

    story.append(Paragraph(f"<b>{escape(labels['technical'])}</b>", h2))
    tech_rows = [
        [labels["pipeline"], escape(a.pipeline_version)],
        [labels["model"], escape(a.model_version)],
    ]
    t_tbl = Table(tech_rows, colWidths=[5.5 * cm, 10.5 * cm])
    t_tbl.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8),
                ("FONT", (1, 0), (1, -1), "Helvetica", 8),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.grey),
                ("LINEABOVE", (0, 0), (-1, 0), 0.25, colors.lightgrey),
                ("LINEBELOW", (0, -1), (-1, -1), 0.25, colors.lightgrey),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_tbl)
    story.append(Spacer(1, 0.45 * cm))

    story.append(Paragraph(f"<b>{escape(labels['disclaimer_heading'])}</b>", h2))
    story.append(Paragraph(escape(a.disclaimer), disclaimer_style))

    doc.build(story)
    out = buf.getvalue()
    buf.close()
    return out
