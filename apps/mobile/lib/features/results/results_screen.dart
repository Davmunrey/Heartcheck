import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/models/analysis_result.dart';
import '../../features/export/export_service.dart';
import '../../theme/app_colors.dart';
import '../../l10n/report_copy.dart';
import '../../widgets/legal_footer.dart';
import '../../widgets/metric_cards.dart';

class ResultsScreen extends StatelessWidget {
  const ResultsScreen({super.key, required this.result});

  final AnalysisResult result;

  String _statusLabel(AppLocalizations t) {
    return switch (result.status) {
      'green' => t.statusGreen,
      'red' => t.statusRed,
      _ => t.statusYellow,
    };
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final rc = ReportCopy.forLang(Localizations.localeOf(context).languageCode);
    return Scaffold(
      appBar: AppBar(
        title: Text(t.resultsTitle),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          tooltip: t.back,
          onPressed: () => context.go('/'),
        ),
      ),
      body: Semantics(
        container: true,
        label: '${t.resultsTitle}: ${result.status}, ${result.classLabel}',
        child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            elevation: 0,
            color: Theme.of(context).colorScheme.primaryContainer.withValues(alpha: 0.35),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  StatusChip(status: result.status, label: _statusLabel(t)),
                  const SizedBox(height: 12),
                  SelectableText(
                    result.message,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: const Color(0xFF1A1A1A),
                          height: 1.45,
                        ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          MetricCard(
            title: t.bpmLabel,
            value: result.bpm?.toStringAsFixed(0) ?? '—',
            subtitle: result.measurementBasis,
          ),
          const SizedBox(height: 8),
          MetricCard(
            title: t.rhythmLabel,
            value: result.rhythmRegularity,
          ),
          const SizedBox(height: 8),
          MetricCard(
            title: t.qualityLabel,
            value: result.extractionQuality.toStringAsFixed(2),
            subtitle: 'confidence ${result.confidenceScore.toStringAsFixed(2)}',
          ),
          const SizedBox(height: 12),
          _RequestIdRow(requestId: result.requestId, copyLabel: rc.copyRequestLabel, copiedLabel: rc.copiedLabel),
          const SizedBox(height: 20),
          SizedBox(
            height: 160,
            child: LineChart(
              LineChartData(
                gridData: const FlGridData(show: false),
                titlesData: const FlTitlesData(show: false),
                borderData: FlBorderData(show: false),
                lineBarsData: [
                  LineChartBarData(
                    spots: List.generate(
                      48,
                      (i) => FlSpot(i.toDouble(), math.sin(i / 4) * result.extractionQuality),
                    ),
                    isCurved: true,
                    color: Theme.of(context).colorScheme.primary,
                    barWidth: 2,
                    dotData: const FlDotData(show: false),
                  ),
                ],
              ),
            ),
          ),
          Text(
            rc.chartCaption,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.textMuted),
          ),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: FilledButton.tonal(
                  onPressed: () => _exportPdf(context, rc),
                  child: Text(t.exportPdf),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton.tonal(
                  onPressed: () => _exportJson(context),
                  child: Text(t.exportJson),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => context.push('/education'),
            icon: const Icon(Icons.menu_book_outlined),
            label: Text(t.education),
          ),
          const SizedBox(height: 16),
          Text(
            result.disclaimer,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textMuted,
                  height: 1.4,
                ),
          ),
          const LegalFooter(),
        ],
      ),
      ),
    );
  }

  Future<void> _exportPdf(BuildContext context, ReportCopy rc) async {
    final t = AppLocalizations.of(context)!;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(t.exportPdf),
        content: Text(t.exportWarning),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(t.back)),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(t.share)),
        ],
      ),
    );
    if (ok != true || !context.mounted) return;
    final locale = Localizations.localeOf(context).languageCode;
    final file = await ExportService().buildBestPdf(
      result,
      copy: rc,
      apiClient: HeartscanApiClient(),
      localeCode: locale,
    );
    final usedFallback = !file.path.contains('server');
    if (usedFallback && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(rc.fallbackLocalPdf)),
      );
    }
    if (!context.mounted) return;
    await ExportService().shareFile(file);
  }

  Future<void> _exportJson(BuildContext context) async {
    final t = AppLocalizations.of(context)!;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(t.exportJson),
        content: Text(t.exportWarning),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(t.back)),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(t.share)),
        ],
      ),
    );
    if (ok != true || !context.mounted) return;
    final file = await ExportService().buildJsonFile(result);
    await ExportService().shareFile(file);
  }
}

class _RequestIdRow extends StatelessWidget {
  const _RequestIdRow({
    required this.requestId,
    required this.copyLabel,
    required this.copiedLabel,
  });

  final String requestId;
  final String copyLabel;
  final String copiedLabel;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.grey.shade100,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: () async {
          await Clipboard.setData(ClipboardData(text: requestId));
          if (context.mounted) {
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(copiedLabel)));
          }
        },
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          child: Row(
            children: [
              Icon(Icons.fingerprint, size: 20, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      copyLabel,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.textMuted),
                    ),
                    SelectableText(
                      requestId,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            fontFamily: 'monospace',
                            color: const Color(0xFF1A1A1A),
                          ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.copy_rounded, size: 20, color: Theme.of(context).colorScheme.primary),
            ],
          ),
        ),
      ),
    );
  }
}
