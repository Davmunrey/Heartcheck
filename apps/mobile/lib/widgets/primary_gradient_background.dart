import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Soft hero background matching web hero gradient.
class PrimaryGradientBackground extends StatelessWidget {
  const PrimaryGradientBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            AppColors.brandLight,
            AppColors.surfaceMuted,
            AppColors.surfaceMuted,
          ],
          stops: [0.0, 0.45, 1.0],
        ),
      ),
      child: child,
    );
  }
}
