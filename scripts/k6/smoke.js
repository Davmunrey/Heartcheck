/**
 * Humo de carga (k6) — extiende el ping de salud con metadatos públicos y, si
 * se ofrece una API key + imagen, una pasada autenticada por `/api/v1/analyze`.
 *
 *   K6_API_URL=http://localhost:8000 k6 run scripts/k6/smoke.js
 *   K6_API_URL=http://localhost:8000 \
 *     K6_API_KEY=dev-key-change-me \
 *     K6_SAMPLE_IMAGE=web_public/static/sample_ecg.png \
 *     k6 run scripts/k6/smoke.js
 */
import http from "k6/http";
import { check, sleep } from "k6";

const base = (__ENV.K6_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const apiKey = __ENV.K6_API_KEY || "";
const samplePath = __ENV.K6_SAMPLE_IMAGE || "";
const sample = samplePath ? open(samplePath, "b") : null;

export const options = {
  vus: Number(__ENV.K6_VUS || 5),
  duration: __ENV.K6_DURATION || "30s",
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<8000"],
  },
};

export default function () {
  const health = http.get(`${base}/health`, { tags: { route: "health" } });
  check(health, { "health 200": (res) => res.status === 200 });

  const meta = http.get(`${base}/api/v1/meta`, { tags: { route: "meta" } });
  check(meta, {
    "meta 200": (res) => res.status === 200,
    "meta has pipeline_version": (res) => !!res.json("pipeline_version"),
  });

  if (apiKey && sample) {
    const formData = {
      file: http.file(sample, "sample_ecg.png", "image/png"),
    };
    const headers = { "X-API-Key": apiKey, "Accept-Language": "es" };
    const analyze = http.post(`${base}/api/v1/analyze`, formData, {
      headers,
      tags: { route: "analyze" },
    });
    check(analyze, {
      "analyze 200": (res) => res.status === 200,
      "analyze has status": (res) => !!res.json("status"),
    });
  }

  sleep(0.3);
}
