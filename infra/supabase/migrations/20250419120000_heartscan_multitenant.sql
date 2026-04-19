-- HeartScan multi-tenant tables + RLS (org_id from Clerk JWT template "supabase")
-- Apply in Supabase SQL editor or via supabase db push.
-- Requires: JWT from Clerk includes claim "org_id" matching companies.id

create extension if not exists "pgcrypto";

-- ---- Core tables ----

create table if not exists public.companies (
  id text primary key,
  name text not null,
  plan text not null default 'free',
  stripe_customer_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.memberships (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references public.companies (id) on delete cascade,
  clerk_user_id text not null,
  role text not null default 'member',
  created_at timestamptz not null default now(),
  unique (company_id, clerk_user_id)
);

create index if not exists memberships_user_idx on public.memberships (clerk_user_id);

create table if not exists public.analyses (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references public.companies (id) on delete cascade,
  clerk_user_id text not null,
  request_id text not null,
  status text not null,
  class_label text,
  confidence text,
  pipeline_version text not null,
  model_version text not null,
  result_json jsonb not null,
  image_storage_path text,
  created_at timestamptz not null default now()
);

create index if not exists analyses_company_created_idx on public.analyses (company_id, created_at desc);
create index if not exists analyses_request_idx on public.analyses (request_id);

create table if not exists public.usage_daily (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references public.companies (id) on delete cascade,
  day date not null,
  count integer not null default 0,
  unique (company_id, day)
);

create table if not exists public.feedback (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references public.companies (id) on delete cascade,
  clerk_user_id text,
  request_id text not null,
  pipeline_version text not null,
  model_version text not null,
  reported_class text,
  suggested_class text,
  comment text,
  analysis_json text not null,
  created_at timestamptz not null default now()
);

create index if not exists feedback_company_idx on public.feedback (company_id);

create table if not exists public.api_keys (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references public.companies (id) on delete cascade,
  name text not null,
  key_hash text not null,
  last4 text not null,
  scopes jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  revoked_at timestamptz
);

create index if not exists api_keys_company_idx on public.api_keys (company_id);

create table if not exists public.audit_log (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references public.companies (id) on delete cascade,
  actor_clerk_id text not null,
  action text not null,
  target text,
  metadata jsonb,
  ip text,
  user_agent text,
  created_at timestamptz not null default now()
);

create index if not exists audit_log_company_created_idx on public.audit_log (company_id, created_at desc);

-- ---- RLS: tenant = auth.jwt() ->> 'org_id' ----

alter table public.companies enable row level security;
alter table public.memberships enable row level security;
alter table public.analyses enable row level security;
alter table public.usage_daily enable row level security;
alter table public.feedback enable row level security;
alter table public.api_keys enable row level security;
alter table public.audit_log enable row level security;

-- Helper: current org from JWT (Clerk template must set org_id)
-- authenticated role when using Supabase client with Clerk JWT

create policy "companies_select_own"
  on public.companies for select
  using (id = (auth.jwt() ->> 'org_id'));

create policy "companies_update_own"
  on public.companies for update
  using (id = (auth.jwt() ->> 'org_id'));

create policy "memberships_select_own"
  on public.memberships for select
  using (company_id = (auth.jwt() ->> 'org_id'));

create policy "analyses_all_own"
  on public.analyses for all
  using (company_id = (auth.jwt() ->> 'org_id'))
  with check (company_id = (auth.jwt() ->> 'org_id'));

create policy "usage_daily_all_own"
  on public.usage_daily for all
  using (company_id = (auth.jwt() ->> 'org_id'))
  with check (company_id = (auth.jwt() ->> 'org_id'));

create policy "feedback_all_own"
  on public.feedback for all
  using (company_id = (auth.jwt() ->> 'org_id'))
  with check (company_id = (auth.jwt() ->> 'org_id'));

create policy "api_keys_all_own"
  on public.api_keys for all
  using (company_id = (auth.jwt() ->> 'org_id'))
  with check (company_id = (auth.jwt() ->> 'org_id'));

create policy "audit_log_select_own"
  on public.audit_log for select
  using (company_id = (auth.jwt() ->> 'org_id'));

create policy "audit_log_insert_own"
  on public.audit_log for insert
  with check (company_id = (auth.jwt() ->> 'org_id'));

-- Service role bypasses RLS by default in Supabase.

-- ---- Storage bucket (private) ----

insert into storage.buckets (id, name, public)
values ('ecg-uploads', 'ecg-uploads', false)
on conflict (id) do nothing;

-- Path convention: {org_id}/{uuid}.ext — first folder segment = company id
create policy "ecg_uploads_select"
  on storage.objects for select
  using (
    bucket_id = 'ecg-uploads'
    and (storage.foldername(name))[1] = (auth.jwt() ->> 'org_id')
  );

create policy "ecg_uploads_insert"
  on storage.objects for insert
  with check (
    bucket_id = 'ecg-uploads'
    and (storage.foldername(name))[1] = (auth.jwt() ->> 'org_id')
  );

create policy "ecg_uploads_update"
  on storage.objects for update
  using (
    bucket_id = 'ecg-uploads'
    and (storage.foldername(name))[1] = (auth.jwt() ->> 'org_id')
  );

create policy "ecg_uploads_delete"
  on storage.objects for delete
  using (
    bucket_id = 'ecg-uploads'
    and (storage.foldername(name))[1] = (auth.jwt() ->> 'org_id')
  );
