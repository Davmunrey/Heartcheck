import type { SupabaseClient } from "@supabase/supabase-js";

export type ClerkWebhookEvent =
  | { type: "organization.created"; data: { id: string; name: string; slug?: string } }
  | { type: "organizationMembership.created"; data: { organization: { id: string }; public_user_data: { user_id: string }; role: string } }
  | { type: "organizationMembership.deleted"; data: { organization: { id: string }; public_user_data: { user_id: string } } }
  | { type: string; data: Record<string, unknown> };

export type HandlerResult =
  | { ok: true }
  | { ok: false; error: string; status: number };

export async function handleClerkEvent(
  event: ClerkWebhookEvent,
  supabase: SupabaseClient
): Promise<HandlerResult> {
  if (event.type === "organization.created") {
    const d = event.data as { id: string; name: string };
    const { error } = await supabase
      .from("companies")
      .upsert({ id: d.id, name: d.name }, { onConflict: "id" });
    if (error) return { ok: false, error: error.message, status: 500 };
    return { ok: true };
  }

  if (event.type === "organizationMembership.created") {
    const d = event.data as {
      organization: { id: string };
      public_user_data: { user_id: string };
      role: string;
    };
    const { error } = await supabase.from("memberships").upsert(
      {
        clerk_user_id: d.public_user_data.user_id,
        company_id: d.organization.id,
        role: d.role,
      },
      { onConflict: "company_id,clerk_user_id" }
    );
    if (error) return { ok: false, error: error.message, status: 500 };
    return { ok: true };
  }

  if (event.type === "organizationMembership.deleted") {
    const d = event.data as {
      organization: { id: string };
      public_user_data: { user_id: string };
    };
    const { error } = await supabase
      .from("memberships")
      .delete()
      .eq("clerk_user_id", d.public_user_data.user_id)
      .eq("company_id", d.organization.id);
    if (error) return { ok: false, error: error.message, status: 500 };
    return { ok: true };
  }

  // Unknown event type — acknowledge without acting
  return { ok: true };
}

export function validateSvixHeaders(headers: {
  get(name: string): string | null;
}): { svixId: string; svixTimestamp: string; svixSignature: string } | null {
  const svixId = headers.get("svix-id");
  const svixTimestamp = headers.get("svix-timestamp");
  const svixSignature = headers.get("svix-signature");
  if (!svixId || !svixTimestamp || !svixSignature) return null;
  return { svixId, svixTimestamp, svixSignature };
}
