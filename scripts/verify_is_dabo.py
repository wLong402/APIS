import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager
db = get_db_manager()
print(db.fetch_one("""
SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
FROM BI_lqx.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME='bi_suite_ship_performance_daily' AND COLUMN_NAME='is_dabo'
"""))
for r in db.fetch_all("""
SELECT is_dabo, COUNT(*) c
FROM BI_lqx.dbo.bi_suite_ship_performance_daily
WHERE biz_date BETWEEN '2026-07-10' AND '2026-07-13'
GROUP BY is_dabo
"""):
    print(r)
