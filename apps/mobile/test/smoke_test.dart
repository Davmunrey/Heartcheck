import 'package:flutter_test/flutter_test.dart';
import 'package:heartscan_mobile/core/models/analysis_result.dart';

void main() {
  test('smoke', () {
    expect(2 + 2, 4);
  });

  group('AnalysisResult.fromJson', () {
    const validPayload = <String, dynamic>{
      'status': 'green',
      'message': 'Ritmo sinusal normal',
      'confidence_score': 0.97,
      'rhythm_regularity': 'regular',
      'class_label': 'Normal',
      'disclaimer': 'Solo informativo; no es diagnóstico.',
      'pipeline_version': '1.0.0',
      'model_version': '2.0.0',
      'extraction_quality': 0.88,
      'request_id': 'req-abc-123',
      'bpm': 72.0,
      'measurement_basis': 'RR intervals',
      'education_topic_ids': ['sinus_rhythm'],
    };

    test('parses a valid payload correctly', () {
      final result = AnalysisResult.fromJson(validPayload);

      expect(result.status, 'green');
      expect(result.message, 'Ritmo sinusal normal');
      expect(result.confidenceScore, closeTo(0.97, 0.0001));
      expect(result.rhythmRegularity, 'regular');
      expect(result.classLabel, 'Normal');
      expect(result.disclaimer, 'Solo informativo; no es diagnóstico.');
      expect(result.pipelineVersion, '1.0.0');
      expect(result.modelVersion, '2.0.0');
      expect(result.extractionQuality, closeTo(0.88, 0.0001));
      expect(result.requestId, 'req-abc-123');
      expect(result.bpm, closeTo(72.0, 0.0001));
      expect(result.measurementBasis, 'RR intervals');
      expect(result.educationTopicIds, ['sinus_rhythm']);
    });

    test('throws when a required field is missing', () {
      final badPayload = Map<String, dynamic>.from(validPayload)
        ..remove('status');

      expect(
        () => AnalysisResult.fromJson(badPayload),
        throwsA(isA<TypeError>()),
      );
    });

    test('throws when a required numeric field has wrong type', () {
      final badPayload = Map<String, dynamic>.from(validPayload)
        ..['confidence_score'] = 'not-a-number';

      expect(
        () => AnalysisResult.fromJson(badPayload),
        throwsA(isA<TypeError>()),
      );
    });
  });
}
