-- Audit log tamper-evidence via hash-chaining.
--
-- Each row stores a SHA-256 hash of (prev_hash || row_content) so that
-- any deletion or modification breaks the chain.  The chain root uses
-- a fixed sentinel.
--
-- Verification: call `public.verify_audit_chain(company_id)` — returns
-- false if any gap or hash mismatch is detected.

-- ---- Add chaining columns ----

alter table public.audit_log
  add column if not exists prev_hash text default null,
  add column if not exists row_hash  text default null;

-- ---- Trigger: populate hashes on INSERT ----

create or replace function public._audit_log_hash_chain()
  returns trigger language plpgsql security definer set search_path = public
as $$
declare
  v_prev_hash text;
  v_content   text;
begin
  -- Get the hash of the most recent row for this company (ordered by created_at).
  select row_hash into v_prev_hash
  from public.audit_log
  where company_id = new.company_id
  order by created_at desc, id desc
  limit 1;

  -- Use a fixed sentinel for the first row.
  v_prev_hash := coalesce(v_prev_hash, 'GENESIS');

  -- Canonical content: id|company_id|actor|action|target|created_at
  v_content := concat_ws('|',
    new.id::text,
    new.company_id,
    new.actor_clerk_id,
    new.action,
    coalesce(new.target, ''),
    to_char(new.created_at, 'YYYY-MM-DD"T"HH24:MI:SS.USOF')
  );

  new.prev_hash := v_prev_hash;
  new.row_hash  := encode(
    digest(v_prev_hash || '|' || v_content, 'sha256'),
    'hex'
  );

  return new;
end;
$$;

create trigger audit_log_hash_chain_trigger
  before insert on public.audit_log
  for each row execute function public._audit_log_hash_chain();

-- ---- Block UPDATE and DELETE on audit_log ----
-- Service role bypasses RLS but NOT triggers, so the block applies universally.

create or replace function public._audit_log_deny_mutation()
  returns trigger language plpgsql as $$
begin
  raise exception 'audit_log is append-only; UPDATE/DELETE are not permitted';
end;
$$;

create trigger audit_log_deny_update
  before update on public.audit_log
  for each row execute function public._audit_log_deny_mutation();

create trigger audit_log_deny_delete
  before delete on public.audit_log
  for each row execute function public._audit_log_deny_mutation();

-- ---- Chain verification function ----

create or replace function public.verify_audit_chain(p_company_id text)
  returns table(row_id uuid, ok boolean, expected_hash text, actual_hash text)
  language plpgsql security definer set search_path = public
as $$
declare
  r            public.audit_log%rowtype;
  v_prev_hash  text := 'GENESIS';
  v_content    text;
  v_expected   text;
begin
  for r in
    select * from public.audit_log
    where company_id = p_company_id
    order by created_at asc, id asc
  loop
    v_content := concat_ws('|',
      r.id::text, r.company_id, r.actor_clerk_id, r.action,
      coalesce(r.target, ''),
      to_char(r.created_at, 'YYYY-MM-DD"T"HH24:MI:SS.USOF')
    );
    v_expected := encode(
      digest(v_prev_hash || '|' || v_content, 'sha256'),
      'hex'
    );
    row_id        := r.id;
    ok            := (r.row_hash = v_expected);
    expected_hash := v_expected;
    actual_hash   := r.row_hash;
    return next;
    v_prev_hash := r.row_hash;
  end loop;
end;
$$;

revoke all on function public.verify_audit_chain(text) from public, authenticated;
