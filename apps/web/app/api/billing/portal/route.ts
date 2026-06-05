import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import { getBillingStatus } from "@/lib/billing/status";

export async function POST(req: Request) {
  const { orgId } = await auth();
  if (!orgId) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const status = await getBillingStatus();
  const secret = process.env.STRIPE_SECRET_KEY;
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL ?? new URL(req.url).origin;
  if (!secret || !status.stripeCustomerId) {
    return NextResponse.json({
      mode: "not_configured",
      message: "Stripe portal unavailable until customer exists.",
    });
  }

  const body = new URLSearchParams({
    customer: status.stripeCustomerId,
    return_url: `${baseUrl}/settings/billing`,
  });
  const res = await fetch("https://api.stripe.com/v1/billing_portal/sessions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${secret}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });
  const data = (await res.json()) as { url?: string; error?: { message?: string } };
  if (!res.ok || !data.url) {
    return NextResponse.json({ error: data.error?.message ?? "stripe portal failed" }, { status: 502 });
  }
  return NextResponse.json({ url: data.url });
}

