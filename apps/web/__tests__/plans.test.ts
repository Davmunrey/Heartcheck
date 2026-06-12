import assert from "node:assert/strict";
import test from "node:test";

import { TRIAL_DAYS, daysLeft, trialEndsAt } from "../lib/billing/plans.ts";

test("daysLeft returns null when end date is missing", () => {
  assert.equal(daysLeft(null), null);
  assert.equal(daysLeft(undefined), null);
});

test("daysLeft returns 0 for a past date (never negative)", () => {
  const past = new Date(Date.now() - 5 * 86_400_000).toISOString();
  assert.equal(daysLeft(past), 0);
});

test("daysLeft ceils remaining days for a future date", () => {
  const future = new Date(Date.now() + 5 * 86_400_000 - 1000).toISOString();
  assert.equal(daysLeft(future), 5);
});

test("trialEndsAt is TRIAL_DAYS after the start", () => {
  const start = new Date("2026-01-01T00:00:00.000Z");
  const end = trialEndsAt(start);
  const diffDays = Math.round((end.getTime() - start.getTime()) / 86_400_000);
  assert.equal(diffDays, TRIAL_DAYS);
});

test("trialEndsAt does not mutate the input date", () => {
  const start = new Date("2026-01-01T00:00:00.000Z");
  const before = start.getTime();
  trialEndsAt(start);
  assert.equal(start.getTime(), before);
});
