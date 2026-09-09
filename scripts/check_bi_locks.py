import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager
db = get_db_manager()

print('object_id:', db.fetch_one(
    "SELECT OBJECT_ID(N'BI_lqx.dbo.bi_suite_ship_performance_daily', N'U') AS oid"
))

print('blockers:')
for r in db.fetch_all("""
SELECT TOP 20
    r.session_id, r.blocking_session_id, r.status, r.wait_type, r.wait_time,
    r.command, DB_NAME(r.database_id) dbname,
    LEFT(REPLACE(REPLACE(t.text, CHAR(13), ' '), CHAR(10), ' '), 200) sql_text
FROM sys.dm_exec_requests r
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE r.blocking_session_id <> 0
   OR r.session_id IN (SELECT blocking_session_id FROM sys.dm_exec_requests WHERE blocking_session_id <> 0)
   OR t.text LIKE '%bi_suite_ship_performance_daily%'
   OR t.text LIKE '%#ship_order%'
   OR t.text LIKE '%stockout_sales_detail%'
ORDER BY r.wait_time DESC
"""):
    print(r)

print('\nlong runners:')
for r in db.fetch_all("""
SELECT TOP 15
    r.session_id, r.status, r.wait_type, r.wait_time, r.total_elapsed_time,
    r.command, DB_NAME(r.database_id) dbname,
    LEFT(REPLACE(REPLACE(t.text, CHAR(13), ' '), CHAR(10), ' '), 180) sql_text
FROM sys.dm_exec_requests r
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE r.session_id <> @@SPID
  AND r.total_elapsed_time > 30000
ORDER BY r.total_elapsed_time DESC
"""):
    print(r)
