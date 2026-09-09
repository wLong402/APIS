import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bi.tasks.suite_ship_performance_daily import _build_select_sql
from core.database import get_db_manager

sql = _build_select_sql('2025-12-01', '2025-12-31')
check = f"""
SELECT COUNT(*) AS rows,
       COUNT(DISTINCT CONCAT(CONVERT(varchar(10), biz_date, 120), '|', suite_no)) AS distinct_pk
FROM (
{sql}
) t
"""
db = get_db_manager()
print(db.fetch_one(check))

dups = db.fetch_all(f"""
SELECT biz_date, suite_no, COUNT(*) AS c
FROM (
{sql}
) t
GROUP BY biz_date, suite_no
HAVING COUNT(*) > 1
""")
print('dups', len(dups))
for r in dups[:5]:
    print(r)
