-- SaaS billing + trial + workflow orchestration metadata.
-- Safe to run after 20250419120000_heartscan_multitenant.sql.

alter table public.companies
  alter column plan set default 'trial',
  add column if not exists stripe_subscription_id text,
  add column if not exists subscription_status text not null default 'trialing',
  add column if not exists trial_ends_at timestamptz not null default (now() + interval '7 days');

create table if not exists public.billing_events (
  id uuid primary key default gen_random_uuid(),
  stripe_event_id text not null unique,
  company_id text not null references public.companies (id) on delete cascade,
  event_type text not null,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists billing_events_company_created_idx
  on public.billing_events (company_id, created_at desc);

create table if not exists public.workflow_runs (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references public.companies (id) on delete cascade,
  workflow_type text not null,
  status text not null default 'running',
  external_id text,
  state jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists workflow_runs_company_status_idx
  on public.workflow_runs (company_id, status);

alter table public.billing_events enable row level security;
alter table public.workflow_runs enable row level security;

create policy "billing_events_select_own"
  on public.billing_events for select
  using (company_id = (auth.jwt() ->> 'org_id'));

create policy "workflow_runs_select_own"
  on public.workflow_runs for select
  using (company_id = (auth.jwt() ->> 'org_id'));

create policy "workflow_runs_insert_own"
  on public.workflow_runs for insert
  with check (company_id = (auth.jwt() ->> 'org_id'));

create policy "workflow_runs_update_own"
  on public.workflow_runs for update
  using (company_id = (auth.jwt() ->> 'org_id'))
  with check (company_id = (auth.jwt() ->> 'org_id'));

-- Billing webhooks use service role. No authenticated insert/update for billing_events.

