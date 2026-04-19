-- Manual RLS checks: run in Supabase SQL editor with JWT role simulation disabled.
-- Replace org ids and use service role only in controlled tests.
--
-- Example intent:
-- 1. As user A (org_1), INSERT into analyses → visible only for org_1 SELECT.
-- 2. As user B (org_2), SELECT must not return org_1 rows.

-- This file documents the procedure; automated CI for RLS requires Supabase test project + anon keys.

select 1 as rls_tests_placeholder;
