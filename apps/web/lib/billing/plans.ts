export type PlanId = "trial" | "clinic" | "hospital" | "enterprise";

export interface Plan {
  id: PlanId;
  name: string;
  price: string;
  tagline: string;
  quota: string;
  features: string[];
  priceEnv?: string;
}

export const TRIAL_DAYS = 7;

export const plans: Plan[] = [
  {
    id: "trial",
    name: "Trial",
    price: "0 EUR",
    tagline: "7 días para validar flujo clínico.",
    quota: "50 análisis",
    features: ["Copilot ECG", "Historial org", "PDF demo", "Audit log"],
  },
  {
    id: "clinic",
    name: "Clinic",
    price: "299 EUR/mes",
    tagline: "Clínicas pequeñas y telemedicina.",
    quota: "2.000 análisis/mes",
    priceEnv: "STRIPE_PRICE_CLINIC",
    features: ["API + consola", "Export PDF", "Soporte email", "Retención configurable"],
  },
  {
    id: "hospital",
    name: "Hospital",
    price: "1.499 EUR/mes",
    tagline: "Equipos multi-sede con gobierno.",
    quota: "25.000 análisis/mes",
    priceEnv: "STRIPE_PRICE_HOSPITAL",
    features: ["SAML/SCIM opcional", "Audit chain", "SLA", "DPA + BAA-ready"],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "Contrato",
    tagline: "Red hospitalaria, aseguradora, OEM.",
    quota: "Custom",
    features: ["VPC/on-prem option", "Model eval pack", "Procurement", "Security review"],
  },
];

export function trialEndsAt(start = new Date()): Date {
  const end = new Date(start);
  end.setDate(end.getDate() + TRIAL_DAYS);
  return end;
}

export function daysLeft(end: string | null | undefined): number | null {
  if (!end) return null;
  const diff = new Date(end).getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / 86_400_000));
}

