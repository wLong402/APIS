import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager
db = get_db_manager()
for t in ['dwd_wdt_stockin_refund', 'dwd_wdt_stockin_refund_detail']:
    cols = [c['COLUMN_NAME'] for c in db.fetch_all(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME=? "
        "AND (COLUMN_NAME LIKE '%time%' OR COLUMN_NAME LIKE '%create%' OR COLUMN_NAME LIKE '%modif%') "
        "ORDER BY ORDINAL_POSITION", (t,)
    )]
    print(t, cols)
print(db.fetch_one("""
SELECT MIN(created_time) mn, MAX(created_time) mx, COUNT_BIG(*) n
FROM dbo.dwd_wdt_stockin_refund WHERE created_time IS NOT NULL
"""))
