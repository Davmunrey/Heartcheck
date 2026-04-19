/// Configure via `--dart-define=HEARTSCAN_API_BASE=...`, `HEARTSCAN_API_KEY=...`,
/// and optionally `HEARTSCAN_ACCESS_TOKEN` (JWT) for authenticated calls.
class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'HEARTSCAN_API_BASE',
    defaultValue: 'http://127.0.0.1:8000',
  );

  static const String apiKey = String.fromEnvironment(
    'HEARTSCAN_API_KEY',
    defaultValue: 'dev-key-change-me',
  );

  /// When set, sent as `Authorization: Bearer` instead of `X-API-Key` for analyze & reports.
  static const String accessToken = String.fromEnvironment(
    'HEARTSCAN_ACCESS_TOKEN',
    defaultValue: '',
  );
}
