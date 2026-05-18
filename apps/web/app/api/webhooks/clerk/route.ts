import { headers } from "next/headers";
import { NextResponse } from "next/server";
import { Webhook } from "svix";
import { createClient } from "@supabase/supabase-js";
import { handleClerkEvent, validateSvixHeaders } from "@/lib/webhooks/clerk-handlers";

/** Sync Clerk org/membership events → Supabase (implement inserts with service role). */
export async function POST(req: Request) {
  const secret = process.env.CLERK_WEBHOOK_SECRET;
  if (!secret) {
    return NextResponse.json({ ok: true, message: "CLERK_WEBHOOK_SECRET not set; noop" });
  }

  const payload = await req.text();
  const h = await headers();
  const svixHeaders = validateSvixHeaders(h);
  if (!svixHeaders) {
    return NextResponse.json({ error: "missing svix headers" }, { status: 400 });
  }

  const wh = new Webhook(secret);
  try {
    wh.verify(payload, {
      "svix-id": svixHeaders.svixId,
      "svix-timestamp": svixHeaders.svixTimestamp,
      "svix-signature": svixHeaders.svixSignature,
    });
  } catch {
    return NextResponse.json({ error: "invalid signature" }, { status: 400 });
  }

  const body = JSON.parse(payload) as {
    type: string;
    data: Record<string, unknown>;
  };

  const supabaseUrl = process.env.SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceRoleKey) {
    console.error("Supabase service role env vars not set");
    return NextResponse.json(
      { error: "Supabase configuration missing" },
      { status: 500 }
    );
  }

  const supabase = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false },
  });

  const result = await handleClerkEvent(body, supabase);
  if (!result.ok) {
    console.error("Webhook handler error:", result.error);
    return NextResponse.json({ error: result.error }, { status: result.status });
  }

  return NextResponse.json({ ok: true });
}
