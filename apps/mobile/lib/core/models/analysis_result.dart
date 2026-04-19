class AnalysisResult {
  const AnalysisResult({
    required this.status,
    required this.message,
    required this.confidenceScore,
    required this.rhythmRegularity,
    required this.classLabel,
    required this.disclaimer,
    required this.pipelineVersion,
    required this.modelVersion,
    required this.extractionQuality,
    required this.requestId,
    this.bpm,
    this.nonReportableReason,
    this.analysisLimit,
    this.measurementBasis,
    this.supportedFindings,
    this.educationTopicIds = const [],
  });

  final String status;
  final String message;
  final double confidenceScore;
  final String rhythmRegularity;
  final String classLabel;
  final String disclaimer;
  final String pipelineVersion;
  final String modelVersion;
  final double extractionQuality;
  final String requestId;
  final double? bpm;
  final Map<String, String>? nonReportableReason;
  final List<String>? analysisLimit;
  final String? measurementBasis;
  final List<String>? supportedFindings;
  final List<String> educationTopicIds;

  factory AnalysisResult.fromJson(Map<String, dynamic> j) {
    return AnalysisResult(
      status: j['status'] as String,
      message: j['message'] as String,
      confidenceScore: (j['confidence_score'] as num).toDouble(),
      rhythmRegularity: j['rhythm_regularity'] as String,
      classLabel: j['class_label'] as String,
      disclaimer: j['disclaimer'] as String,
      pipelineVersion: j['pipeline_version'] as String,
      modelVersion: j['model_version'] as String,
      extractionQuality: (j['extraction_quality'] as num).toDouble(),
      requestId: j['request_id'] as String,
      bpm: (j['bpm'] as num?)?.toDouble(),
      nonReportableReason: (j['non_reportable_reason'] as Map?)?.map(
        (k, v) => MapEntry(k.toString(), v.toString()),
      ),
      analysisLimit: (j['analysis_limit'] as List?)?.map((e) => e.toString()).toList(),
      measurementBasis: j['measurement_basis'] as String?,
      supportedFindings: (j['supported_findings'] as List?)?.map((e) => e.toString()).toList(),
      educationTopicIds: (j['education_topic_ids'] as List?)?.map((e) => e.toString()).toList() ?? const [],
    );
  }

  Map<String, dynamic> toJson() => {
        'status': status,
        'message': message,
        'confidence_score': confidenceScore,
        'rhythm_regularity': rhythmRegularity,
        'class_label': classLabel,
        'disclaimer': disclaimer,
        'pipeline_version': pipelineVersion,
        'model_version': modelVersion,
        'extraction_quality': extractionQuality,
        'request_id': requestId,
        'bpm': bpm,
        'non_reportable_reason': nonReportableReason,
        'analysis_limit': analysisLimit,
        'measurement_basis': measurementBasis,
        'supported_findings': supportedFindings,
        'education_topic_ids': educationTopicIds,
      };
}
