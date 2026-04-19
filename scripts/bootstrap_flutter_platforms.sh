#!/usr/bin/env bash
set -euo pipefail
# One-time: generate web/android/ios scaffolding for `apps/mobile/` when missing.
cd "$(dirname "$0")/../mobile"
if ! command -v flutter >/dev/null 2>&1; then
  echo "flutter not found in PATH" >&2
  exit 1
fi
flutter create . --platforms=web,android,ios --project-name heartscan
