import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';

/// Legal footer + link to the "When NOT to use HeartScan" guidance.
///
/// The URL is pinned to the public docs path; if the documentation moves,
/// update [whenNotToUseUrl] and regenerate the localized strings.
class LegalFooter extends StatelessWidget {
  const LegalFooter({super.key});

  static const String whenNotToUseUrl =
      'https://github.com/heartscan/heartscan/blob/main/docs/WHEN_NOT_TO_USE.md';

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final style = Theme.of(context).textTheme.bodySmall?.copyWith(
          color: const Color(0xFF424242),
          fontSize: 12,
          height: 1.35,
        );
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      child: Column(
        children: [
          Text(t.legalFooter, textAlign: TextAlign.center, style: style),
          const SizedBox(height: 6),
          SelectableText(
            'Cuándo NO usar HeartScan: $whenNotToUseUrl',
            textAlign: TextAlign.center,
            style: style,
          ),
        ],
      ),
    );
  }
}
