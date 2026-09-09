import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager
db = get_db_manager()

cols = db.fetch_all(
    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='dwd_wdt_stockin_refund_wide' "
    "ORDER BY ORDINAL_POSITION"
)
print('refund_wide columns:', [c['COLUMN_NAME'] for c in cols])

row = db.fetch_one('SELECT TOP 1 * FROM dbo.dwd_wdt_stockin_refund_wide')
if row:
    print('sample keys:', list(row.keys()))
