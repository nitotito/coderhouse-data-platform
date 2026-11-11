-- Run ONCE in the clean temporary warehouse as its deployment owner.
-- Password-disabled SQL test identity: no AWS/IAM user or password is created.
CREATE USER checkpoint6_access_test PASSWORD DISABLE;
GRANT ROLE checkpoint6_analyst TO checkpoint6_access_test;

-- Explicit membership, separate from role-to-role and object privilege grants.
SELECT user_name,role_name,admin_option
FROM svv_user_grants
WHERE user_name='checkpoint6_access_test'
  AND role_name='checkpoint6_analyst';

-- Keep these statements in ONE session. Owner must be allowed to switch identity.
SET SESSION AUTHORIZATION checkpoint6_access_test;
SELECT current_user AS effective_user;
SELECT user_name,role_name,admin_option
FROM svv_user_grants
WHERE user_name=current_user AND role_name='checkpoint6_analyst';
SELECT COUNT(*) AS visible_metric_rows FROM analytics.transactions_per_minute;
SELECT COUNT(*) AS visible_join_rows FROM analytics.recent_vs_iceberg;
RESET SESSION AUTHORIZATION;

-- Expected-denial tests are in redshift-security-smoke.py, not unhandled errors
-- in this consolidated script. Capture membership + effective_user + allow/deny.
