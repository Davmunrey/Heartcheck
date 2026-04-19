import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:go_router/go_router.dart';

import '../../theme/app_colors.dart';
import '../../widgets/legal_footer.dart';
import '../../widgets/primary_gradient_background.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      body: PrimaryGradientBackground(
        child: SafeArea(
          child: Column(
            children: [
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                  child: Column(
                    children: [
                      const SizedBox(height: 8),
                      Material(
                        elevation: 3,
                        shadowColor: AppColors.brand.withValues(alpha: 0.25),
                        shape: const CircleBorder(),
                        color: Colors.white,
                        child: Padding(
                          padding: const EdgeInsets.all(22),
                          child: Icon(
                            Icons.monitor_heart_outlined,
                            size: 56,
                            color: cs.primary,
                          ),
                        ),
                      ),
                      const SizedBox(height: 24),
                      Text(
                        t.appTitle,
                        style: Theme.of(context).textTheme.displaySmall,
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        t.onboardingBody,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              fontSize: 15,
                              height: 1.45,
                            ),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 32),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed: () => context.push('/camera'),
                          child: Text(t.scanEcg),
                        ),
                      ),
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton(
                          onPressed: () => context.push('/camera?gallery=1'),
                          child: Text(t.fromGallery),
                        ),
                      ),
                      const SizedBox(height: 20),
                      TextButton.icon(
                        onPressed: () => context.push('/onboarding'),
                        icon: const Icon(Icons.tips_and_updates_outlined, size: 20),
                        label: Text(t.onboardingTitle),
                      ),
                      TextButton.icon(
                        onPressed: () => context.push('/education'),
                        icon: const Icon(Icons.menu_book_outlined, size: 20),
                        label: Text(t.education),
                      ),
                    ],
                  ),
                ),
              ),
              const Padding(
                padding: EdgeInsets.fromLTRB(24, 0, 24, 8),
                child: LegalFooter(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
