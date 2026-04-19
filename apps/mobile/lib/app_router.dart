import 'package:go_router/go_router.dart';

import 'core/models/analysis_result.dart';
import 'features/camera/camera_screen.dart';
import 'features/education/education_screen.dart';
import 'features/home/home_screen.dart';
import 'features/onboarding/onboarding_screen.dart';
import 'features/results/results_screen.dart';

GoRouter createRouter() {
  return GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, __) => const HomeScreen(),
      ),
      GoRoute(
        path: '/onboarding',
        builder: (_, __) => const OnboardingScreen(),
      ),
      GoRoute(
        path: '/camera',
        builder: (ctx, st) {
          final gallery = st.uri.queryParameters['gallery'] == '1';
          return CameraScreen(openGalleryFirst: gallery);
        },
      ),
      GoRoute(
        path: '/results',
        builder: (_, st) {
          final r = st.extra as AnalysisResult;
          return ResultsScreen(result: r);
        },
      ),
      GoRoute(
        path: '/education',
        builder: (_, __) => const EducationScreen(),
      ),
    ],
  );
}
