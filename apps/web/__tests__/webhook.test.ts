import assert from "node:assert/strict";
import test from "node:test";
import { handleClerkEvent, validateSvixHeaders } from "../lib/webhooks/clerk-handlers.ts";

// ── validateSvixHeaders ────────────────────────────────────────────────────

test("validateSvixHeaders: returns null when all headers missing", () => {
  const result = validateSvixHeaders({ get: () => null });
  assert.equal(result, null);
});

test("validateSvixHeaders: returns null when svix-id missing", () => {
  const result = validateSvixHeaders({
    get: (k) => (k === "svix-id" ? null : "value"),
  });
  assert.equal(result, null);
});

test("validateSvixHeaders: returns null when svix-timestamp missing", () => {
  const result = validateSvixHeaders({
    get: (k) => (k === "svix-timestamp" ? null : "value"),
  });
  assert.equal(result, null);
});

test("validateSvixHeaders: returns null when svix-signature missing", () => {
  const result = validateSvixHeaders({
    get: (k) => (k === "svix-signature" ? null : "value"),
  });
  assert.equal(result, null);
});

test("validateSvixHeaders: returns header object when all present", () => {
  const result = validateSvixHeaders({
    get: (k) => {
      const m: Record<string, string> = {
        "svix-id": "id-1",
        "svix-timestamp": "99999",
        "svix-signature": "v1,abc",
      };
      return m[k] ?? null;
    },
  });
  assert.deepEqual(result, {
    svixId: "id-1",
    svixTimestamp: "99999",
    svixSignature: "v1,abc",
  });
});

// ── Stub SupabaseClient ────────────────────────────────────────────────────

function makeSupabase({
  upsertError = null as { message: string } | null,
  deleteError = null as { message: string } | null,
} = {}) {
  const calls: { table: string; op: string; data?: unknown }[] = [];
  const eqChain = {
    eq: (_col: string, _val: string) => eqChain,
    then: (resolve: (v: { error: null }) => void) => resolve({ error: deleteError }),
  };
  return {
    calls,
    client: {
      from: (table: string) => ({
        upsert: (data: unknown) => {
          calls.push({ table, op: "upsert", data });
          return Promise.resolve({ error: upsertError });
        },
        delete: () => {
          calls.push({ table, op: "delete" });
          return eqChain;
        },
      }),
    } as unknown as import("@supabase/supabase-js").SupabaseClient,
  };
}

// ── handleClerkEvent ───────────────────────────────────────────────────────

test("organization.created: upserts company and returns ok", async () => {
  const { calls, client } = makeSupabase();
  const result = await handleClerkEvent(
    { type: "organization.created", data: { id: "org_1", name: "Org One" } },
    client
  );
  assert.deepEqual(result, { ok: true });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].table, "companies");
  assert.equal(calls[0].op, "upsert");
});

test("organization.created: supabase error → returns error result", async () => {
  const { client } = makeSupabase({ upsertError: { message: "constraint violation" } });
  const result = await handleClerkEvent(
    { type: "organization.created", data: { id: "org_1", name: "Org One" } },
    client
  );
  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.ok(result.error.includes("constraint violation"));
    assert.equal(result.status, 500);
  }
});

test("organizationMembership.created: upserts membership", async () => {
  const { calls, client } = makeSupabase();
  const result = await handleClerkEvent(
    {
      type: "organizationMembership.created",
      data: {
        organization: { id: "org_1" },
        public_user_data: { user_id: "user_a" },
        role: "admin",
      },
    },
    client
  );
  assert.deepEqual(result, { ok: true });
  assert.equal(calls[0].table, "memberships");
  assert.equal(calls[0].op, "upsert");
});

test("organizationMembership.deleted: deletes membership", async () => {
  const { calls, client } = makeSupabase();
  const result = await handleClerkEvent(
    {
      type: "organizationMembership.deleted",
      data: {
        organization: { id: "org_1" },
        public_user_data: { user_id: "user_a" },
      },
    },
    client
  );
  assert.deepEqual(result, { ok: true });
  assert.equal(calls[0].table, "memberships");
  assert.equal(calls[0].op, "delete");
});

test("organizationMembership.deleted: supabase error → returns error result", async () => {
  const { client } = makeSupabase({ deleteError: { message: "not found" } });
  const result = await handleClerkEvent(
    {
      type: "organizationMembership.deleted",
      data: {
        organization: { id: "org_1" },
        public_user_data: { user_id: "user_x" },
      },
    },
    client
  );
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.status, 500);
});

test("unknown event type: returns ok without touching DB", async () => {
  const { calls, client } = makeSupabase();
  const result = await handleClerkEvent(
    { type: "user.created", data: { id: "u1" } },
    client
  );
  assert.deepEqual(result, { ok: true });
  assert.equal(calls.length, 0);
});
