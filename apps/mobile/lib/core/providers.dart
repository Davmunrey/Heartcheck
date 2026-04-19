import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

final heartscanApiProvider = Provider<HeartscanApiClient>(
  (ref) => HeartscanApiClient(),
);
