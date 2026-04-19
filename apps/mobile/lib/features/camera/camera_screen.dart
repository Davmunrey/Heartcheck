import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/providers.dart';
import '../../l10n/ui_copy.dart';
import '../../theme/app_colors.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/legal_footer.dart';

class CameraScreen extends ConsumerStatefulWidget {
  const CameraScreen({super.key, this.openGalleryFirst = false});

  final bool openGalleryFirst;

  @override
  ConsumerState<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends ConsumerState<CameraScreen> {
  CameraController? _controller;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (widget.openGalleryFirst) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _pickGallery());
    } else {
      _initCamera();
    }
  }

  Future<void> _initCamera() async {
    try {
      final cams = await availableCameras();
      if (cams.isEmpty) {
        setState(() {
          _loading = false;
          _error = 'no_camera';
        });
        return;
      }
      final ctrl = CameraController(cams.first, ResolutionPreset.medium, enableAudio: false);
      await ctrl.initialize();
      setState(() {
        _controller = ctrl;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _error = '$e';
      });
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _captureAndAnalyze() async {
    final ctrl = _controller;
    if (ctrl == null || !ctrl.value.isInitialized) return;
    setState(() => _loading = true);
    try {
      final shot = await ctrl.takePicture();
      final bytes = await shot.readAsBytes();
      await _send(bytes, 'capture.jpg');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _pickGallery() async {
    final picker = ImagePicker();
    final x = await picker.pickImage(source: ImageSource.gallery);
    if (x == null) {
      if (mounted) context.pop();
      return;
    }
    final bytes = await x.readAsBytes();
    await _send(bytes, x.name);
  }

  Future<void> _send(Uint8List bytes, String name) async {
    final t = AppLocalizations.of(context)!;
    final locale = Localizations.localeOf(context).toLanguageTag();
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => PopScope(
        canPop: false,
        child: AlertDialog(
          content: Row(
            children: [
              const CircularProgressIndicator(),
              const SizedBox(width: 20),
              Expanded(child: Text(t.analyzing)),
            ],
          ),
        ),
      ),
    );
    try {
      final client = ref.read(heartscanApiProvider);
      final result = await client.analyzeImage(bytes, name, acceptLanguage: locale);
      if (!mounted) return;
      Navigator.of(context, rootNavigator: true).pop();
      context.push('/results', extra: result);
    } catch (e) {
      if (!mounted) return;
      Navigator.of(context, rootNavigator: true).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${t.errorGeneric} ($e)')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final lang = Localizations.localeOf(context).languageCode;
    if (widget.openGalleryFirst) {
      return Scaffold(
        body: Center(
          child: Semantics(
            label: t.analyzing,
            child: const CircularProgressIndicator(),
          ),
        ),
      );
    }
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.black.withValues(alpha: 0.35),
        foregroundColor: Colors.white,
        title: Text(t.scanEcg),
      ),
      body: Column(
        children: [
          Expanded(
            child: _loading && _controller == null && _error == null
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? EmptyState(
                        icon: Icons.videocam_off_outlined,
                        title: _error == 'no_camera'
                            ? UiCopy.cameraNoCamera(lang)
                            : _error!,
                        action: FilledButton.tonal(
                          onPressed: _pickGallery,
                          child: Text(t.fromGallery),
                        ),
                      )
                    : _controller == null
                        ? const SizedBox.shrink()
                        : Stack(
                            fit: StackFit.expand,
                            children: [
                              CameraPreview(_controller!),
                              CustomPaint(
                                painter: _FramePainter(),
                                child: const SizedBox.expand(),
                              ),
                              Positioned(
                                left: 16,
                                right: 16,
                                bottom: 100,
                                child: Material(
                                  color: Colors.black54,
                                  borderRadius: BorderRadius.circular(12),
                                  child: Padding(
                                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                    child: Text(
                                      t.onboardingBody,
                                      style: const TextStyle(color: Colors.white, fontSize: 13),
                                      textAlign: TextAlign.center,
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
          ),
          if (_controller != null && _error == null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(24, 16, 24, 12),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.88),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
              ),
              child: SafeArea(
                top: false,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    Semantics(
                      button: true,
                      label: t.fromGallery,
                      child: IconButton(
                        onPressed: _loading ? null : _pickGallery,
                        icon: const Icon(Icons.photo_library_outlined),
                        color: Colors.white,
                        iconSize: 28,
                        style: IconButton.styleFrom(
                          backgroundColor: Colors.white24,
                          minimumSize: const Size(52, 52),
                        ),
                      ),
                    ),
                    Semantics(
                      button: true,
                      label: t.scanEcg,
                      child: Material(
                        color: AppColors.brand,
                        shape: const CircleBorder(),
                        elevation: 4,
                        child: InkWell(
                          onTap: _loading ? null : _captureAndAnalyze,
                          customBorder: const CircleBorder(),
                          child: SizedBox(
                            width: 72,
                            height: 72,
                            child: _loading
                                ? const Center(
                                    child: SizedBox(
                                      width: 28,
                                      height: 28,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2.5,
                                        color: Colors.white,
                                      ),
                                    ),
                                  )
                                : const Icon(Icons.camera_alt, color: Colors.white, size: 32),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ColoredBox(
            color: AppColors.surfaceMuted,
            child: const LegalFooter(),
          ),
        ],
      ),
    );
  }
}

class _FramePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final r = RRect.fromRectAndRadius(
      Rect.fromCenter(
        center: Offset(size.width / 2, size.height / 2),
        width: size.width * 0.88,
        height: size.height * 0.55,
      ),
      const Radius.circular(14),
    );
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.92)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;
    canvas.drawRRect(r, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
