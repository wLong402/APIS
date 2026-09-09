import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager
db = get_db_manager()
print('cols:', [c['COLUMN_NAME'] for c in db.fetch_all("""
SELECT COLUMN_NAME FROM BI_lqx.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME='bi_suite_ship_performance_daily' ORDER BY ORDINAL_POSITION
""")])
print(db.fetch_one("""
SELECT COUNT(*) n,
       COUNT(DISTINCT shop_code) shops,
       SUM(CASE WHEN is_dabo=1 THEN 1 ELSE 0 END) dabo_rows,
       SUM(CASE WHEN is_dabo=0 THEN 1 ELSE 0 END) non_dabo_rows,
       SUM(ship_amount) ship, SUM(refund_amount) refund
FROM BI_lqx.dbo.bi_suite_ship_performance_daily
WHERE biz_date BETWEEN '2026-07-10' AND '2026-07-13'
"""))
print('same suite multi shop:')
for r in db.fetch_all("""
SELECT TOP 3 biz_date, suite_no, COUNT(DISTINCT shop_code) shops
FROM BI_lqx.dbo.bi_suite_ship_performance_daily
WHERE biz_date BETWEEN '2026-07-10' AND '2026-07-13'
GROUP BY biz_date, suite_no
HAVING COUNT(DISTINCT shop_code) > 1
ORDER BY shops DESC
"""):
    print(r)
print('sample:')
for r in db.fetch_all("""
SELECT TOP 5 biz_date, suite_no, shop_code, is_dabo, ship_amount, refund_amount, net_amount
FROM BI_lqx.dbo.bi_suite_ship_performance_daily
WHERE biz_date BETWEEN '2026-07-10' AND '2026-07-13'
ORDER BY ship_amount DESC
"""):
    print(r)
