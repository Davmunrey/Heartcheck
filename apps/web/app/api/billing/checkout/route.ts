import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import { plans } from "@/lib/billing/plans";

export async function POST(req: Request) {
  const { orgId, userId } = await auth();
  if (!orgId || !userId) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const { planId } = (await req.json().catch(() => ({}))) as { planId?: string };
  const plan = plans.find((p) => p.id === planId);
  if (!plan || plan.id === "trial" || plan.id === "enterprise") {
    return NextResponse.json({ error: "invalid plan" }, { status: 400 });
  }

  const secret = process.env.STRIPE_SECRET_KEY;
  const priceId = plan.priceEnv ? process.env[plan.priceEnv] : undefined;
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL ?? new URL(req.url).origin;
  if (!secret || !priceId) {
    return NextResponse.json({
      mode: "not_configured",
      message: "Stripe env missing. Set STRIPE_SECRET_KEY and plan price id.",
      plan: plan.id,
    });
  }

  const body = new URLSearchParams({
    mode: "subscription",
    "line_items[0][price]": priceId,
    "line_items[0][quantity]": "1",
    success_url: `${baseUrl}/settings/billing?checkout=success`,
    cancel_url: `${baseUrl}/pricing?checkout=cancel`,
    client_reference_id: orgId,
    "metadata[org_id]": orgId,
    "metadata[user_id]": userId,
  });

  const res = await fetch("https://api.stripe.com/v1/checkout/sessions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${secret}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });
  const data = (await res.json()) as { url?: string; error?: { message?: string } };
  if (!res.ok || !data.url) {
    return NextResponse.json({ error: data.error?.message ?? "stripe checkout failed" }, { status: 502 });
  }
  return NextResponse.json({ url: data.url });
}

