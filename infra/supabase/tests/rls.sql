-- HeartScan RLS isolation tests using pgTAP.
-- Run via: supabase test db
-- Requires pgTAP extension (enabled in Supabase by default).
--
-- Strategy: insert fixture rows as postgres role, then switch to
-- authenticated + set request.jwt.claims to simulate each tenant's JWT.
-- All changes roll back at the end — no persistent state.

begin;

select plan(28);

-- ── Setup ──────────────────────────────────────────────────────────────────

set local role postgres;

insert into public.companies (id, name, plan) values
  ('org_a', 'Org Alpha', 'free'),
  ('org_b', 'Org Beta',  'free');

-- analyses rows for both tenants
insert into public.analyses
  (company_id, clerk_user_id, request_id, status, pipeline_version, model_version, result_json)
values
  ('org_a', 'user_a1', 'req_a1', 'ok', '0.1', '0.1', '{}'),
  ('org_b', 'user_b1', 'req_b1', 'ok', '0.1', '0.1', '{}');

-- memberships
insert into public.memberships (company_id, clerk_user_id, role) values
  ('org_a', 'user_a1', 'admin'),
  ('org_b', 'user_b1', 'member');

-- usage_daily
insert into public.usage_daily (company_id, day, count) values
  ('org_a', current_date, 5),
  ('org_b', current_date, 3);

-- feedback
insert into public.feedback
  (company_id, clerk_user_id, request_id, pipeline_version, model_version, analysis_json)
values
  ('org_a', 'user_a1', 'req_a1', '0.1', '0.1', '{}'),
  ('org_b', 'user_b1', 'req_b1', '0.1', '0.1', '{}');

-- api_keys
insert into public.api_keys (company_id, name, key_hash, last4) values
  ('org_a', 'key-alpha', 'hash_a', 'aaaa'),
  ('org_b', 'key-beta',  'hash_b', 'bbbb');

-- audit_log (inserted directly as postgres — bypasses RLS)
insert into public.audit_log (company_id, actor_clerk_id, action) values
  ('org_a', 'user_a1', 'login'),
  ('org_b', 'user_b1', 'login');


-- ── Helper: set tenant JWT ─────────────────────────────────────────────────

-- Switch to authenticated role and set org_id claim
create or replace function tests.set_tenant(org text) returns void as $$
begin
  perform set_config('request.jwt.claims', json_build_object('org_id', org)::text, true);
  set local role authenticated;
end;
$$ language plpgsql;


-- ── analyses ──────────────────────────────────────────────────────────────

select tests.set_tenant('org_a');

select is(
  (select count(*)::int from public.analyses),
  1,
  'analyses: org_a sees exactly 1 own row'
);
select is(
  (select company_id from public.analyses limit 1),
  'org_a',
  'analyses: org_a row has correct company_id'
);
select is(
  (select count(*)::int from public.analyses where company_id = 'org_b'),
  0,
  'analyses: org_a cannot see org_b rows'
);

-- INSERT with correct org allowed
select lives_ok(
  $$insert into public.analyses
      (company_id, clerk_user_id, request_id, status, pipeline_version, model_version, result_json)
    values ('org_a', 'user_a1', 'req_a2', 'ok', '0.1', '0.1', '{}')$$,
  'analyses: org_a can insert own row'
);

-- INSERT with wrong org blocked
select throws_ok(
  $$insert into public.analyses
      (company_id, clerk_user_id, request_id, status, pipeline_version, model_version, result_json)
    values ('org_b', 'user_a1', 'req_x', 'ok', '0.1', '0.1', '{}')$$,
  'analyses: org_a cannot insert row for org_b'
);

select tests.set_tenant('org_b');

select is(
  (select count(*)::int from public.analyses),
  1,
  'analyses: org_b sees only own row'
);


-- ── companies ─────────────────────────────────────────────────────────────

select tests.set_tenant('org_a');

select is(
  (select count(*)::int from public.companies),
  1,
  'companies: org_a sees only own company'
);
select is(
  (select id from public.companies limit 1),
  'org_a',
  'companies: org_a sees correct company id'
);
select is(
  (select count(*)::int from public.companies where id = 'org_b'),
  0,
  'companies: org_a cannot see org_b company'
);

-- UPDATE own allowed
select lives_ok(
  $$update public.companies set name = 'Org Alpha Updated' where id = 'org_a'$$,
  'companies: org_a can update own row'
);

-- UPDATE other org blocked (no rows affected, not an error — verify 0 rows)
select is(
  (select count(*)::int from public.companies where id = 'org_b' and name = 'hacked'),
  0,
  'companies: org_a update on org_b affects 0 rows'
);


-- ── memberships ───────────────────────────────────────────────────────────

select tests.set_tenant('org_a');

select is(
  (select count(*)::int from public.memberships),
  1,
  'memberships: org_a sees only own memberships'
);
select is(
  (select count(*)::int from public.memberships where company_id = 'org_b'),
  0,
  'memberships: org_a cannot see org_b memberships'
);


-- ── usage_daily ───────────────────────────────────────────────────────────

select tests.set_tenant('org_a');

select is(
  (select count(*)::int from public.usage_daily),
  1,
  'usage_daily: org_a sees only own row'
);
select is(
  (select count(*)::int from public.usage_daily where company_id = 'org_b'),
  0,
  'usage_daily: org_a cannot see org_b row'
);


-- ── feedback ──────────────────────────────────────────────────────────────

select tests.set_tenant('org_a');

select is(
  (select count(*)::int from public.feedback),
  1,
  'feedback: org_a sees only own rows'
);
select is(
  (select count(*)::int from public.feedback where company_id = 'org_b'),
  0,
  'feedback: org_a cannot see org_b feedback'
);


-- ── api_keys ──────────────────────────────────────────────────────────────

select tests.set_tenant('org_a');

select is(
  (select count(*)::int from public.api_keys),
  1,
  'api_keys: org_a sees only own keys'
);
select is(
  (select count(*)::int from public.api_keys where company_id = 'org_b'),
  0,
  'api_keys: org_a cannot see org_b keys'
);


-- ── audit_log ─────────────────────────────────────────────────────────────

select tests.set_tenant('org_a');

select is(
  (select count(*)::int from public.audit_log),
  1,
  'audit_log: org_a sees only own entries'
);

-- INSERT own allowed
select lives_ok(
  $$insert into public.audit_log (company_id, actor_clerk_id, action)
    values ('org_a', 'user_a1', 'test_event')$$,
  'audit_log: org_a can insert own entry'
);

-- INSERT for other org blocked
select throws_ok(
  $$insert into public.audit_log (company_id, actor_clerk_id, action)
    values ('org_b', 'user_a1', 'evil_event')$$,
  'audit_log: org_a cannot insert entry for org_b'
);

select is(
  (select count(*)::int from public.audit_log where company_id = 'org_b'),
  0,
  'audit_log: org_a cannot read org_b entries'
);


-- ── Finish ────────────────────────────────────────────────────────────────

select * from finish();
rollback;
