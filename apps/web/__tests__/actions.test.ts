import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_ANALYZE_FILE_SIZE,
  validateAnalyzeFile,
} from "../lib/analyze/validation.ts";

test("validateAnalyzeFile throws when no file attached", () => {
  assert.throws(() => validateAnalyzeFile(null), /Falta el archivo de imagen\./);
});

test("validateAnalyzeFile throws when file exceeds 10 MB", () => {
  const oversizedBlob = new Blob([new Uint8Array(MAX_ANALYZE_FILE_SIZE + 1)], {
    type: "image/jpeg",
  });

  assert.throws(
    () => validateAnalyzeFile(oversizedBlob),
    /El archivo supera el límite de 10 MB/
  );
});

test("validateAnalyzeFile returns blob when file valid", () => {
  const blob = new Blob(["fake-image-data"], { type: "image/jpeg" });
  assert.equal(validateAnalyzeFile(blob), blob);
});
