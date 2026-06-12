import assert from "node:assert/strict";
import test from "node:test";

import {
  DiagnosticParseError,
  parseDiagnosticResponse,
} from "../lib/analyze/diagnostic.ts";

test("parseDiagnosticResponse throws on null / non-object", () => {
  assert.throws(() => parseDiagnosticResponse(null), DiagnosticParseError);
  assert.throws(() => parseDiagnosticResponse("nope"), DiagnosticParseError);
});

test("parseDiagnosticResponse throws when findings is not an array", () => {
  assert.throws(() => parseDiagnosticResponse({ findings: "x" }), DiagnosticParseError);
});

test("parseDiagnosticResponse parses a valid payload and maps findings", () => {
  const out = parseDiagnosticResponse({
    abnormal: true,
    requires_review: true,
    macro_auroc: 0.88,
    n_leads: 12,
    sampling_rate_hz: 500,
    model_version: "ecg_27class",
    pipeline_version: "0.1.0",
    request_id: "abc-123",
    disclaimer: "decision support",
    analysis_limit: ["SINGLE_SOURCE"],
    findings: [
      { code: "AF", label: "Fibrilación auricular", probability: 0.91, positive: true, threshold: 0.5, uncertain: false, confidence: "high", auroc: 0.93 },
    ],
  });
  assert.equal(out.abnormal, true);
  assert.equal(out.findings.length, 1);
  assert.equal(out.findings[0].code, "AF");
  assert.equal(out.findings[0].positive, true);
  assert.equal(out.macro_auroc, 0.88);
});

test("parseDiagnosticResponse applies defensive defaults", () => {
  const out = parseDiagnosticResponse({
    findings: [
      // missing confidence + auroc; uncertain true -> confidence defaults to "low"
      { code: "PVC", probability: 0.3, threshold: 0.5, uncertain: true },
    ],
  });
  assert.equal(out.findings[0].confidence, "low");
  assert.equal(out.findings[0].auroc, 0);
  assert.equal(out.findings[0].label, "PVC"); // falls back to code
  assert.equal(out.n_leads, 12); // default when absent
  assert.equal(out.model_version, "unknown");
});

test("parseDiagnosticResponse throws when a finding probability is not numeric", () => {
  assert.throws(
    () => parseDiagnosticResponse({ findings: [{ code: "AF", probability: "x", threshold: 0.5 }] }),
    DiagnosticParseError,
  );
});
