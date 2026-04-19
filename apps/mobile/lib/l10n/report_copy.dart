/// Localized strings for PDF export (kept in sync with ARB where possible).
class ReportCopy {
  const ReportCopy({
    required this.docTitle,
    required this.docSubtitle,
    required this.sectionInterpretation,
    required this.sectionTechnical,
    required this.sectionLimits,
    required this.sectionNonReportable,
    required this.sectionFindings,
    required this.sectionMetrics,
    required this.labelClass,
    required this.labelConfidence,
    required this.labelTopics,
    required this.generatedUtc,
    required this.requestIdLabel,
    required this.chartCaption,
    required this.fallbackLocalPdf,
    required this.copyRequestLabel,
    required this.copiedLabel,
  });

  final String docTitle;
  final String docSubtitle;
  final String sectionInterpretation;
  final String sectionTechnical;
  final String sectionLimits;
  final String sectionNonReportable;
  final String sectionFindings;
  final String sectionMetrics;
  final String labelClass;
  final String labelConfidence;
  final String labelTopics;
  final String generatedUtc;
  final String requestIdLabel;
  final String chartCaption;
  final String fallbackLocalPdf;
  final String copyRequestLabel;
  final String copiedLabel;

  static ReportCopy forLang(String? code) {
    final c = (code ?? 'en').toLowerCase();
    if (c.startsWith('es')) return _es;
    return _en;
  }

  static const _en = ReportCopy(
    docTitle: 'HeartScan analysis report',
    docSubtitle: 'Educational wellbeing software — not a certified medical device.',
    sectionInterpretation: 'Interpretation',
    sectionTechnical: 'Technical traceability',
    sectionLimits: 'Limitations & coverage',
    sectionNonReportable: 'Non-reportable',
    sectionFindings: 'Documented findings (this release)',
    sectionMetrics: 'Key metrics',
    labelClass: 'Classification',
    labelConfidence: 'Model confidence',
    labelTopics: 'Education topics',
    generatedUtc: 'Generated (UTC)',
    requestIdLabel: 'Request ID',
    chartCaption: 'Illustrative curve (not your ECG)',
    fallbackLocalPdf: 'Sharing a device-generated PDF (server report unavailable).',
    copyRequestLabel: 'Copy request ID',
    copiedLabel: 'Copied to clipboard',
  );

  static const _es = ReportCopy(
    docTitle: 'Informe de análisis HeartScan',
    docSubtitle: 'Software educativo de bienestar — no es un dispositivo médico certificado.',
    sectionInterpretation: 'Interpretación',
    sectionTechnical: 'Trazabilidad técnica',
    sectionLimits: 'Limitaciones y cobertura',
    sectionNonReportable: 'No informable',
    sectionFindings: 'Hallazgos documentados (esta versión)',
    sectionMetrics: 'Métricas clave',
    labelClass: 'Clasificación',
    labelConfidence: 'Confianza del modelo',
    labelTopics: 'Temas educativos',
    generatedUtc: 'Generado (UTC)',
    requestIdLabel: 'ID de solicitud',
    chartCaption: 'Curva ilustrativa (no es su ECG)',
    fallbackLocalPdf: 'Compartiendo PDF generado en el dispositivo (informe del servidor no disponible).',
    copyRequestLabel: 'Copiar ID de solicitud',
    copiedLabel: 'Copiado al portapapeles',
  );
}
