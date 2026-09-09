import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager
db = get_db_manager()
print('max consign:', db.fetch_one('SELECT MAX(consign_time) AS mx FROM dbo.dwd_wdt_stockout_sales_wide'))
print('jul window:', db.fetch_one(
    "SELECT COUNT_BIG(*) AS n FROM dbo.dwd_wdt_stockout_sales_wide "
    "WHERE consign_time >= '2026-07-07' AND consign_time < '2026-07-11'"
))
print('bi table max:', db.fetch_one('SELECT MAX(biz_date) AS mx, COUNT(*) AS n FROM dbo.bi_suite_ship_performance_daily'))
