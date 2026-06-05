import { createHmac, timingSafeEqual } from "node:crypto";
import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

function verifyStripeSignature(payload: string, header: string | null, secret: string): boolean {
  if (!header) return false;
  const parts = Object.fromEntries(
    header.split(",").map((item) => {
      const [k, v] = item.split("=");
      return [k, v];
    })
  );
  if (!parts.t || !parts.v1) return false;
  const signedPayload = `${parts.t}.${payload}`;
  const digest = createHmac("sha256", secret).update(signedPayload).digest("hex");
  const expected = Buffer.from(digest);
  const actual = Buffer.from(parts.v1);
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}

export async function POST(req: Request) {
  const secret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!secret) {
    return NextResponse.json({ ok: true, message: "STRIPE_WEBHOOK_SECRET not set; noop" });
  }

  const payload = await req.text();
  if (!verifyStripeSignature(payload, req.headers.get("stripe-signature"), secret)) {
    return NextResponse.json({ error: "invalid signature" }, { status: 400 });
  }

  const event = JSON.parse(payload) as {
    id: string;
    type: string;
    data: { object: Record<string, unknown> };
  };

  const supabaseUrl = process.env.SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceRoleKey) {
    return NextResponse.json({ error: "Supabase configuration missing" }, { status: 500 });
  }

  const supabase = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false },
  });

  const obj = event.data.object;
  const metadata = (obj.metadata ?? {}) as Record<string, string>;
  const orgId = metadata.org_id ?? String(obj.client_reference_id ?? "");
  if (!orgId) return NextResponse.json({ ok: true, ignored: "missing org_id" });

  const subscriptionId = String(obj.subscription ?? obj.id ?? "");
  const customerId = String(obj.customer ?? "");
  const status = String(obj.status ?? (event.type.includes("deleted") ? "canceled" : "active"));
  const plan = event.type.includes("deleted") ? "trial" : "paid";

  if (
    event.type === "checkout.session.completed" ||
    event.type === "customer.subscription.updated" ||
    event.type === "customer.subscription.deleted"
  ) {
    const { error } = await supabase
      .from("companies")
      .update({
        plan,
        stripe_customer_id: customerId || null,
        stripe_subscription_id: subscriptionId || null,
        subscription_status: status,
        updated_at: new Date().toISOString(),
      })
      .eq("id", orgId);
    if (error) return NextResponse.json({ error: error.message }, { status: 500 });

    await supabase.from("billing_events").upsert(
      {
        stripe_event_id: event.id,
        company_id: orgId,
        event_type: event.type,
        payload: event,
      },
      { onConflict: "stripe_event_id" }
    );
  }

  return NextResponse.json({ ok: true });
}
