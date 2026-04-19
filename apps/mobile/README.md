# HeartScan mobile (Flutter)

## Setup

1. Install [Flutter](https://docs.flutter.dev/get-started/install) (stable).
2. If platform folders (`android/`, `ios/`) are missing, from this directory run:

   ```bash
   flutter create . --project-name heartscan_mobile --org com.heartscan.app
   ```

3. Fetch packages and generate localizations:

   ```bash
   flutter pub get
   flutter gen-l10n
   ```

4. Run (with API running locally):

   ```bash
   flutter run --dart-define=HEARTSCAN_API_BASE=http://127.0.0.1:8000 --dart-define=HEARTSCAN_API_KEY=dev-key-change-me
   ```

Use `10.0.2.2` instead of `127.0.0.1` for Android emulator.

## Tests

```bash
flutter test
```
