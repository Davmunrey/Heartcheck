/// Short UI strings by locale (keeps ARB small; sync with translations if needed).
abstract final class UiCopy {
  static List<String> onboardingBullets(String? languageCode) {
    final c = (languageCode ?? 'en').toLowerCase();
    if (c.startsWith('es')) {
      return const [
        'Luz suave y uniforme; evite reflejos en el papel.',
        'Mantenga la tira plana y dentro del marco.',
        'Si el resultado no es claro, repita la foto.',
      ];
    }
    return const [
      'Even, soft lighting — avoid glare on the paper.',
      'Keep the strip flat and fully inside the frame.',
      'If the result looks unclear, retake the photo.',
    ];
  }

  static String cameraNoCamera(String? languageCode) {
    final c = (languageCode ?? 'en').toLowerCase();
    if (c.startsWith('es')) {
      return 'No hay cámara disponible en este dispositivo.';
    }
    return 'No camera found on this device.';
  }
}
