import { describe, expect, it } from "vitest";
import { AnalysisResponseSchema, parseAnalysisResponse } from "../index.js";

const VALID: Record<string, unknown> = {
  status: "green",
  bpm: 72,
  message: "Normal sinus rhythm.",
  confidence_score: 0.95,
  rhythm_regularity: "regular",
  class_label: "normal",
  disclaimer: "This is a screening tool only.",
  pipeline_version: "0.1.0",
  model_version: "ecg-resnet1d-0.1.0-trained",
  extraction_quality: 0.9,
  request_id: "abc-123",
};

describe("AnalysisResponseSchema — valid payloads", () => {
  it("parses a minimal valid response", () => {
    const result = AnalysisResponseSchema.parse(VALID);
    expect(result.status).toBe("green");
    expect(result.class_label).toBe("normal");
    expect(result.education_topic_ids).toEqual([]);
  });

  it("accepts null bpm", () => {
    const result = AnalysisResponseSchema.parse({ ...VALID, bpm: null });
    expect(result.bpm).toBeNull();
  });

  it("accepts all status variants", () => {
    for (const status of ["green", "yellow", "red"] as const) {
      const result = AnalysisResponseSchema.parse({ ...VALID, status });
      expect(result.status).toBe(status);
    }
  });

  it("accepts all class_label variants", () => {
    for (const label of ["normal", "arrhythmia", "noise"] as const) {
      const result = AnalysisResponseSchema.parse({ ...VALID, class_label: label });
      expect(result.class_label).toBe(label);
    }
  });

  it("accepts all rhythm_regularity variants", () => {
    for (const r of ["regular", "irregular", "unknown"] as const) {
      const result = AnalysisResponseSchema.parse({ ...VALID, rhythm_regularity: r });
      expect(result.rhythm_regularity).toBe(r);
    }
  });

  it("populates education_topic_ids default when absent", () => {
    const result = AnalysisResponseSchema.parse(VALID);
    expect(Array.isArray(result.education_topic_ids)).toBe(true);
  });

  it("accepts optional fields when present", () => {
    const result = AnalysisResponseSchema.parse({
      ...VALID,
      non_reportable_reason: { low_confidence: "confidence < 0.6" },
      analysis_limit: ["SINGLE_LEAD_PHOTO"],
      supported_findings: ["three_class_screening"],
      measurement_basis: "ASSUMED_UNIFORM_TIME_AXIS",
      prediction_set: ["normal", "arrhythmia"],
      calibrated_confidence: 0.88,
      quality_reasons: ["blurry"],
      lead_count_detected: 1,
    });
    expect(result.calibrated_confidence).toBe(0.88);
    expect(result.lead_count_detected).toBe(1);
  });

  it("accepts optional fields when absent (undefined)", () => {
    const result = AnalysisResponseSchema.parse(VALID);
    expect(result.non_reportable_reason).toBeUndefined();
    expect(result.prediction_set).toBeUndefined();
  });
});

describe("AnalysisResponseSchema — invalid payloads", () => {
  it("throws on unknown status value", () => {
    expect(() =>
      AnalysisResponseSchema.parse({ ...VALID, status: "blue" })
    ).toThrow();
  });

  it("throws on unknown class_label", () => {
    expect(() =>
      AnalysisResponseSchema.parse({ ...VALID, class_label: "tachycardia" })
    ).toThrow();
  });

  it("throws on unknown rhythm_regularity", () => {
    expect(() =>
      AnalysisResponseSchema.parse({ ...VALID, rhythm_regularity: "erratic" })
    ).toThrow();
  });

  it("throws when confidence_score > 1", () => {
    expect(() =>
      AnalysisResponseSchema.parse({ ...VALID, confidence_score: 1.5 })
    ).toThrow();
  });

  it("throws when confidence_score < 0", () => {
    expect(() =>
      AnalysisResponseSchema.parse({ ...VALID, confidence_score: -0.1 })
    ).toThrow();
  });

  it("throws when extraction_quality > 1", () => {
    expect(() =>
      AnalysisResponseSchema.parse({ ...VALID, extraction_quality: 2 })
    ).toThrow();
  });

  it("throws when required field missing (pipeline_version)", () => {
    const { pipeline_version: _, ...rest } = VALID;
    expect(() => AnalysisResponseSchema.parse(rest)).toThrow();
  });

  it("throws when required field missing (request_id)", () => {
    const { request_id: _, ...rest } = VALID;
    expect(() => AnalysisResponseSchema.parse(rest)).toThrow();
  });

  it("throws when lead_count_detected is not integer", () => {
    expect(() =>
      AnalysisResponseSchema.parse({ ...VALID, lead_count_detected: 1.5 })
    ).toThrow();
  });
});

describe("parseAnalysisResponse async wrapper", () => {
  it("resolves with parsed object for valid input", async () => {
    const result = await parseAnalysisResponse(VALID);
    expect(result.status).toBe("green");
  });

  it("rejects for invalid input", async () => {
    await expect(parseAnalysisResponse({ ...VALID, status: "unknown" })).rejects.toThrow();
  });
});
