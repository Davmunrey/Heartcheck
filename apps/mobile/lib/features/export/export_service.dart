import 'dart:convert';
import 'dart:io';

import 'package:intl/intl.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:share_plus/share_plus.dart';

import '../../core/api_client.dart';
import '../../core/models/analysis_result.dart';
import '../../l10n/report_copy.dart';

class ExportService {
  /// Prefer server PDF (aligned with API); fall back to rich local PDF.
  Future<File> buildBestPdf(
    AnalysisResult r, {
    required ReportCopy copy,
    HeartscanApiClient? apiClient,
    String localeCode = 'en',
  }) async {
    final api = apiClient ?? HeartscanApiClient();
    final info = await PackageInfo.fromPlatform();
    try {
      final bytes = await api.fetchReportPdf(
        r,
        locale: localeCode,
        appVersion: info.version,
      );
      if (bytes != null && bytes.isNotEmpty) {
        return _writeTemp(bytes, 'heartscan_report_server.pdf');
      }
    } catch (_) {
      /* fallback below */
    }
    return buildPdf(r, copy: copy, appVersion: info.version);
  }

  Future<File> buildPdf(
    AnalysisResult r, {
    required ReportCopy copy,
    String appVersion = '0.1.0',
  }) async {
    final doc = pw.Document();
    final statusColor = _statusPdfColor(r.status);
    final ts = DateFormat("yyyy-MM-dd HH:mm:ss'Z'").format(DateTime.now().toUtc());

    doc.addPage(
      pw.MultiPage(
        pageTheme: pw.PageTheme(
          margin: const pw.EdgeInsets.symmetric(horizontal: 44, vertical: 48),
          theme: pw.ThemeData.withFont(
            base: pw.Font.helvetica(),
            bold: pw.Font.helveticaBold(),
          ),
        ),
        build: (ctx) => [
          pw.Text(
            copy.docTitle,
            style: pw.TextStyle(
              fontSize: 20,
              fontWeight: pw.FontWeight.bold,
              color: PdfColors.blue900,
            ),
          ),
          pw.SizedBox(height: 6),
          pw.Text(
            copy.docSubtitle,
            style: const pw.TextStyle(fontSize: 9, color: PdfColors.grey800),
          ),
          pw.SizedBox(height: 16),
          pw.Row(
            mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
            children: [
              pw.Expanded(
                child: pw.Text(
                  '${copy.requestIdLabel}: ${r.requestId}',
                  style: const pw.TextStyle(fontSize: 8, color: PdfColors.grey700),
                ),
              ),
              pw.Text(
                '$ts · ${copy.generatedUtc}',
                style: const pw.TextStyle(fontSize: 8, color: PdfColors.grey700),
              ),
            ],
          ),
          pw.SizedBox(height: 6),
          pw.Text(
            'App v$appVersion',
            style: const pw.TextStyle(fontSize: 8, color: PdfColors.grey600),
          ),
          pw.SizedBox(height: 14),
          pw.Container(
            padding: const pw.EdgeInsets.all(10),
            decoration: pw.BoxDecoration(
              color: statusColor,
              borderRadius: pw.BorderRadius.circular(6),
              border: pw.Border.all(color: PdfColors.grey400, width: 0.5),
            ),
            child: pw.Text(
              '${r.status.toUpperCase()} · ${copy.labelClass}: ${r.classLabel}',
              style: const pw.TextStyle(fontSize: 11),
            ),
          ),
          pw.SizedBox(height: 16),
          pw.Text(
            copy.sectionMetrics,
            style: pw.TextStyle(fontSize: 12, fontWeight: pw.FontWeight.bold),
          ),
          pw.SizedBox(height: 8),
          _metricsTable(r, copy),
          pw.SizedBox(height: 16),
          pw.Text(
            copy.sectionInterpretation,
            style: pw.TextStyle(fontSize: 12, fontWeight: pw.FontWeight.bold),
          ),
          pw.SizedBox(height: 6),
          pw.Text(
            r.message,
            style: const pw.TextStyle(fontSize: 10, lineSpacing: 1.35),
          ),
          if (r.nonReportableReason != null && r.nonReportableReason!.isNotEmpty) ...[
            pw.SizedBox(height: 12),
            pw.Text(
              copy.sectionNonReportable,
              style: pw.TextStyle(fontSize: 11, fontWeight: pw.FontWeight.bold),
            ),
            pw.SizedBox(height: 4),
            ...r.nonReportableReason!.entries.map(
              (e) => pw.Text(
                '${e.key}: ${e.value}',
                style: const pw.TextStyle(fontSize: 8, color: PdfColors.grey800),
              ),
            ),
          ],
          if (r.analysisLimit != null && r.analysisLimit!.isNotEmpty) ...[
            pw.SizedBox(height: 14),
            pw.Text(
              copy.sectionLimits,
              style: pw.TextStyle(fontSize: 11, fontWeight: pw.FontWeight.bold),
            ),
            pw.SizedBox(height: 6),
            ..._bullets(r.analysisLimit!),
          ],
          if (r.supportedFindings != null && r.supportedFindings!.isNotEmpty) ...[
            pw.SizedBox(height: 12),
            pw.Text(
              copy.sectionFindings,
              style: pw.TextStyle(fontSize: 11, fontWeight: pw.FontWeight.bold),
            ),
            pw.SizedBox(height: 6),
            ..._bullets(r.supportedFindings!),
          ],
          if (r.educationTopicIds.isNotEmpty) ...[
            pw.SizedBox(height: 12),
            pw.Text(
              copy.labelTopics,
              style: pw.TextStyle(fontSize: 11, fontWeight: pw.FontWeight.bold),
            ),
            pw.SizedBox(height: 4),
            pw.Text(
              r.educationTopicIds.join(', '),
              style: const pw.TextStyle(fontSize: 9),
            ),
          ],
          pw.SizedBox(height: 16),
          pw.Text(
            copy.sectionTechnical,
            style: pw.TextStyle(fontSize: 11, fontWeight: pw.FontWeight.bold),
          ),
          pw.SizedBox(height: 6),
          pw.Text(
            'Pipeline ${r.pipelineVersion} · Model ${r.modelVersion}',
            style: const pw.TextStyle(fontSize: 9),
          ),
          pw.SizedBox(height: 16),
          pw.Divider(thickness: 0.5, color: PdfColors.grey400),
          pw.SizedBox(height: 8),
          pw.Text(
            r.disclaimer,
            style: const pw.TextStyle(
              fontSize: 8,
              color: PdfColors.grey800,
              lineSpacing: 1.25,
            ),
          ),
        ],
      ),
    );
    final dir = await getTemporaryDirectory();
    final f = File('${dir.path}/heartscan_report.pdf');
    await f.writeAsBytes(await doc.save());
    return f;
  }

  List<pw.Widget> _bullets(List<String> items) {
    return items
        .map(
          (e) => pw.Padding(
            padding: const pw.EdgeInsets.only(left: 6, bottom: 3),
            child: pw.Text('• $e', style: const pw.TextStyle(fontSize: 9)),
          ),
        )
        .toList();
  }

  pw.Widget _metricsTable(AnalysisResult r, ReportCopy copy) {
    final data = <List<String>>[
      ['Metric', 'Value'],
      [copy.labelClass, r.classLabel],
      [copy.labelConfidence, r.confidenceScore.toStringAsFixed(2)],
      ['BPM', r.bpm?.toStringAsFixed(0) ?? '—'],
      ['Rhythm', r.rhythmRegularity],
      ['Quality', r.extractionQuality.toStringAsFixed(2)],
    ];
    if (r.measurementBasis != null) {
      data.add(['BPM basis', r.measurementBasis!]);
    }
    return pw.Table.fromTextArray(
      data: data,
      border: pw.TableBorder.all(color: PdfColors.grey400, width: 0.35),
      headerStyle: pw.TextStyle(fontWeight: pw.FontWeight.bold, fontSize: 9),
      headerDecoration: const pw.BoxDecoration(color: PdfColors.grey300),
      cellStyle: const pw.TextStyle(fontSize: 9),
      cellHeight: 20,
      cellAlignments: {
        0: pw.Alignment.centerLeft,
        1: pw.Alignment.centerLeft,
      },
    );
  }

  PdfColor _statusPdfColor(String status) {
    return switch (status) {
      'green' => PdfColor.fromInt(0xFFE8F5E9),
      'red' => PdfColor.fromInt(0xFFFFEBEE),
      _ => PdfColor.fromInt(0xFFFFF8E1),
    };
  }

  Future<File> _writeTemp(List<int> bytes, String name) async {
    final dir = await getTemporaryDirectory();
    final f = File('${dir.path}/$name');
    await f.writeAsBytes(bytes);
    return f;
  }

  Future<File> buildJsonFile(AnalysisResult r) async {
    final dir = await getTemporaryDirectory();
    final f = File('${dir.path}/heartscan_analysis.json');
    await f.writeAsString(const JsonEncoder.withIndent('  ').convert(r.toJson()));
    return f;
  }

  Future<void> shareFile(File file) async {
    await Share.shareXFiles([XFile(file.path)]);
  }
}
