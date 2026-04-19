import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:http/http.dart' as http;

import '../../core/api_config.dart';
import '../../theme/app_colors.dart';
import '../../widgets/legal_footer.dart';

class EducationScreen extends StatefulWidget {
  const EducationScreen({super.key});

  @override
  State<EducationScreen> createState() => _EducationScreenState();
}

class _EducationScreenState extends State<EducationScreen> {
  String? _locale;
  Future<List<dynamic>>? _future;

  Future<List<dynamic>> _load(String loc) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/api/v1/education/topics').replace(
      queryParameters: {'locale': loc},
    );
    final r = await http.get(uri);
    if (r.statusCode != 200) {
      throw Exception('HTTP ${r.statusCode}');
    }
    final map = jsonDecode(r.body) as Map<String, dynamic>;
    return map['topics'] as List<dynamic>;
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final loc = Localizations.localeOf(context).languageCode;
    if (_locale != loc) {
      _locale = loc;
      _future = _load(loc);
    }
    return Scaffold(
      appBar: AppBar(title: Text(t.education)),
      body: FutureBuilder<List<dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.cloud_off_outlined, size: 48, color: AppColors.brand.withValues(alpha: 0.7)),
                    const SizedBox(height: 12),
                    Text(
                      t.errorGeneric,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.brandDark),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '${snap.error}',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.textMuted),
                    ),
                  ],
                ),
              ),
            );
          }
          final topics = snap.data ?? [];
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            itemCount: topics.length + 1,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (ctx, i) {
              if (i == topics.length) {
                return const Padding(
                  padding: EdgeInsets.only(top: 16),
                  child: LegalFooter(),
                );
              }
              final item = topics[i] as Map<String, dynamic>;
              final title = item['title']?.toString() ?? '';
              final summary = item['summary']?.toString() ?? '';
              return Card(
                child: ListTile(
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  leading: CircleAvatar(
                    backgroundColor: AppColors.brandLight,
                    foregroundColor: AppColors.brand,
                    child: const Icon(Icons.article_outlined, size: 22),
                  ),
                  title: Text(
                    title,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                          color: AppColors.brandDark,
                        ),
                  ),
                  subtitle: Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      summary,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.4),
                    ),
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
