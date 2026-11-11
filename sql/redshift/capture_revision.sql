-- Revision 11/11/2026. Query Editor v2, workgroup coderhouse-dev-analytics,
-- database analytics. Execute one SELECT at a time; show SQL + result grid.

-- 1. Typed stream fields and actual Kinesis arrival, not only historical Event Time.
SELECT transaction_id,event_time,arrival_timestamp,amount,payment_method,status
FROM analytics.transactions_typed
WHERE validation_error IS NULL
ORDER BY payment_method,event_time;

-- 2. One row per UTC minute/payment method, including rejected records.
SELECT window_start,payment_method,transaction_count,total_amount,
       average_amount,approved_count,rejected_count,approved_amount
FROM analytics.transactions_per_minute
ORDER BY window_start DESC;

-- 3. Equivalent approved metrics against the existing Iceberg snapshot.
SELECT payment_method,recent_approved_count,iceberg_approved_count,
       recent_approved_amount,iceberg_approved_amount,
       count_difference,amount_difference
FROM analytics.recent_vs_iceberg;

-- 4. The console user's own effective membership. Root IAM != SQL table owner.
SELECT current_user AS effective_user,user_name,role_name,admin_option
FROM svv_user_grants
WHERE user_name=current_user AND role_name='checkpoint6_analyst';
