# Reporting (PDF / JSON)

## API

- **`POST /api/v1/reports/pdf`**: generates a structured **PDF** from a prior `AnalysisResponse` JSON (no image). Requires **Bearer JWT** or legacy **`X-API-Key`** when `HEARTSCAN_ALLOW_LEGACY_API_KEY=true`.
- Response headers: `Content-Disposition: attachment; filename="heartscan_report_<request_id>.pdf"`.

Implementation: `app/services/pdf_report.py` (ReportLab platypus, EN/ES copy, metrics table, interpretation, limits, supported findings, technical block, disclaimer).

## Mobile

- **`ExportService.buildBestPdf`**: tries the **server PDF** first (same layout as API integrations), then falls back to a **rich local PDF** (`package:pdf`).
- Configure **`HEARTSCAN_ACCESS_TOKEN`** (JWT) or **`HEARTSCAN_API_KEY`** via `--dart-define` so `/reports/pdf` can authenticate.
- Localized labels: `apps/mobile/lib/l10n/report_copy.dart` (mirror with ARB/`flutter gen-l10n` if you consolidate strings later).

## JSON export

- Client-side **`heartscan_analysis.json`** from `AnalysisResult.toJson()` (unchanged contract).
