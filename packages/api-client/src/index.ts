import { z } from "zod";

/** Mirrors FastAPI `AnalysisResponse` — keep in sync with apps/ml-api/app/schemas/analysis.ts */
export const AnalysisResponseSchema = z.object({
  status: z.enum(["green", "yellow", "red"]),
  bpm: z.number().nullable(),
  message: z.string(),
  confidence_score: z.number().min(0).max(1),
  rhythm_regularity: z.enum(["regular", "irregular", "unknown"]),
  class_label: z.enum(["normal", "arrhythmia", "noise"]),
  disclaimer: z.string(),
  pipeline_version: z.string(),
  model_version: z.string(),
  extraction_quality: z.number().min(0).max(1),
  request_id: z.string(),
  non_reportable_reason: z.record(z.string()).nullable().optional(),
  analysis_limit: z.array(z.string()).nullable().optional(),
  supported_findings: z.array(z.string()).nullable().optional(),
  measurement_basis: z.string().nullable().optional(),
  education_topic_ids: z.array(z.string()).default([]),
  prediction_set: z.array(z.string()).nullable().optional(),
  calibrated_confidence: z.number().min(0).max(1).nullable().optional(),
  quality_reasons: z.array(z.string()).nullable().optional(),
  lead_count_detected: z.number().int().min(1).nullable().optional(),
});

export type AnalysisResponse = z.infer<typeof AnalysisResponseSchema>;

export async function parseAnalysisResponse(data: unknown): Promise<AnalysisResponse> {
  return AnalysisResponseSchema.parse(data);
}
