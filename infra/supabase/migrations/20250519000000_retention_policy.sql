-- Retention and disposal policy for PHI-adjacent tables.
--
-- Regulatory basis: HIPAA minimum necessary + 6-year retention for covered
-- entities (45 CFR §164.530(j)).  Adjust `retention_days` per legal review.
--
-- NOTE: these functions are advisory helpers — actual scheduled invocation
-- must be wired via pg_cron (Supabase Pro) or an external cron job.
-- A pg_cron example is included at the bottom as a comment.

-- ---- Retention metadata column (trigger-maintained) ----
-- A STORED generated column can't use `timestamptz + interval` (Postgres treats
-- it as non-immutable). Use a plain column + trigger instead.

alter table public.analyses add column if not exists purge_after timestamptz;
alter table public.feedback add column if not exists purge_after timestamptz;

create or replace function public.set_purge_after() returns trigger
  language plpgsql set search_path = public
as $$
begin
  new.purge_after := new.created_at + interval '2190 days'; -- ≈ 6 years
  return new;
end;
$$;

drop trigger if exists analyses_set_purge_after on public.analyses;
create trigger analyses_set_purge_after
  before insert or update of created_at on public.analyses
  for each row execute function public.set_purge_after();

drop trigger if exists feedback_set_purge_after on public.feedback;
create trigger feedback_set_purge_after
  before insert or update of created_at on public.feedback
  for each row execute function public.set_purge_after();

-- Backfill any existing rows.
update public.analyses set purge_after = created_at + interval '2190 days' where purge_after is null;
update public.feedback set purge_after = created_at + interval '2190 days' where purge_after is null;

-- ---- Soft-delete: mark rows instead of hard-delete ----

alter table public.analyses add column if not exists deleted_at timestamptz default null;
alter table public.feedback add column if not exists deleted_at timestamptz default null;

-- Partial index so active-row queries stay fast after many soft-deletes.
create index if not exists analyses_active_idx
  on public.analyses (company_id, created_at desc)
  where deleted_at is null;

create index if not exists feedback_active_idx
  on public.feedback (company_id, created_at desc)
  where deleted_at is null;

-- ---- Disposal helpers ----

-- Hard-delete rows past their retention window (run by cron, service role only).
create or replace function public.purge_expired_analyses() returns bigint
  language plpgsql security definer set search_path = public
as $$
declare
  deleted_count bigint;
begin
  delete from public.analyses where purge_after < now();
  get diagnostics deleted_count = row_count;
  return deleted_count;
end;
$$;

create or replace function public.purge_expired_feedback() returns bigint
  language plpgsql security definer set search_path = public
as $$
declare
  deleted_count bigint;
begin
  delete from public.feedback where purge_after < now();
  get diagnostics deleted_count = row_count;
  return deleted_count;
end;
$$;

revoke all on function public.purge_expired_analyses() from public, authenticated;
revoke all on function public.purge_expired_feedback() from public, authenticated;

-- Soft-delete single analysis (user-facing "delete my data" request).
create or replace function public.soft_delete_analysis(p_id uuid, p_company_id text)
  returns void language plpgsql security definer set search_path = public
as $$
begin
  update public.analyses
  set deleted_at = now()
  where id = p_id and company_id = p_company_id and deleted_at is null;
end;
$$;

-- ---- Storage: ECG upload retention (guarded — only if Storage is provisioned) ----
-- Objects in ecg-uploads are named {org_id}/{uuid}.ext. Helper lists objects
-- older than N days for manual review or deletion via the Storage API.
do $$
begin
  if exists (
    select 1 from information_schema.tables
    where table_schema = 'storage' and table_name = 'objects'
  ) then
    execute $f$
      create or replace function public.list_expired_ecg_uploads(retention_days int default 2190)
        returns table(name text, created_at timestamptz, age_days numeric)
        language sql security definer set search_path = storage
      as $body$
        select
          name,
          created_at,
          round(extract(epoch from (now() - created_at)) / 86400, 1) as age_days
        from storage.objects
        where bucket_id = 'ecg-uploads'
          and created_at < now() - (retention_days || ' days')::interval
        order by created_at;
      $body$;
    $f$;
    execute $f$revoke all on function public.list_expired_ecg_uploads(int) from public, authenticated$f$;
  end if;
end $$;

-- ---- pg_cron example (requires pg_cron extension, Supabase Pro) ----
-- Uncomment and run once to schedule nightly purge at 02:00 UTC:
--
-- select cron.schedule(
--   'purge-expired-analyses',
--   '0 2 * * *',
--   $$ select public.purge_expired_analyses(); $$
-- );
-- select cron.schedule(
--   'purge-expired-feedback',
--   '5 2 * * *',
--   $$ select public.purge_expired_feedback(); $$
-- );
