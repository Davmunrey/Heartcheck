import { NextResponse } from "next/server";
import { getBillingStatus } from "@/lib/billing/status";

export async function GET() {
  return NextResponse.json(await getBillingStatus());
}

