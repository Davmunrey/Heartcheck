import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';

import 'api_config.dart';
import 'models/analysis_result.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;
}

class HeartscanApiClient {
  HeartscanApiClient({http.Client? httpClient, Uuid? uuid})
      : _http = httpClient ?? http.Client(),
        _uuid = uuid ?? const Uuid();

  final http.Client _http;
  final Uuid _uuid;

  Map<String, String> _authHeaders() {
    if (ApiConfig.accessToken.isNotEmpty) {
      return {'Authorization': 'Bearer ${ApiConfig.accessToken}'};
    }
    return {'X-API-Key': ApiConfig.apiKey};
  }

  Future<AnalysisResult> analyzeImage(
    List<int> bytes,
    String filename, {
    String acceptLanguage = 'en',
  }) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/api/v1/analyze');
    final req = http.MultipartRequest('POST', uri)
      ..headers.addAll(_authHeaders())
      ..headers['Accept-Language'] = acceptLanguage
      ..headers['X-Request-Id'] = _uuid.v4()
      ..files.add(
        http.MultipartFile.fromBytes('file', bytes, filename: filename),
      );
    final streamed = await _http.send(req);
    final body = await streamed.stream.bytesToString();
    if (streamed.statusCode < 200 || streamed.statusCode >= 300) {
      throw ApiException(body, statusCode: streamed.statusCode);
    }
    final map = jsonDecode(body) as Map<String, dynamic>;
    return AnalysisResult.fromJson(map);
  }

  /// Server-generated PDF (same layout as web integrations). Returns null on non-2xx.
  Future<List<int>?> fetchReportPdf(
    AnalysisResult result, {
    String locale = 'en',
    String appVersion = '0.1.0',
  }) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/api/v1/reports/pdf');
    final res = await _http.post(
      uri,
      headers: {
        ..._authHeaders(),
        'Content-Type': 'application/json',
        'Accept': 'application/pdf',
      },
      body: jsonEncode({
        'analysis': result.toJson(),
        'app_version': appVersion,
        'locale': locale,
      }),
    );
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.bodyBytes;
    }
    return null;
  }
}
