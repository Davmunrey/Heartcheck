import { headers } from "next/headers";
import { NextResponse } from "next/server";
import { Webhook } from "svix";

/** Sync Clerk org/membership events → Supabase (implement inserts with service role). */
export async function POST(req: Request) {
  const secret = process.env.CLERK_WEBHOOK_SECRET;
  if (!secret) {
    return NextResponse.json({ ok: true, message: "CLERK_WEBHOOK_SECRET not set; noop" });
  }

  const payload = await req.text();
  const h = await headers();
  const svixId = h.get("svix-id");
  const svixTimestamp = h.get("svix-timestamp");
  const svixSignature = h.get("svix-signature");
  if (!svixId || !svixTimestamp || !svixSignature) {
    return NextResponse.json({ error: "missing svix headers" }, { status: 400 });
  }

  const wh = new Webhook(secret);
  try {
    wh.verify(payload, {
      "svix-id": svixId,
      "svix-timestamp": svixTimestamp,
      "svix-signature": svixSignature,
    });
  } catch {
    return NextResponse.json({ error: "invalid signature" }, { status: 400 });
  }

  // const body = JSON.parse(payload);
  // TODO: upsert companies / memberships via Supabase service role
  return NextResponse.json({ ok: true });
}
