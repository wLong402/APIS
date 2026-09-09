import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager
db = get_db_manager()
SUITE = 'DK0004000000Z16'

print('=== 源表整体日期覆盖 ===')
print('stockout consign:', db.fetch_one(
    'SELECT MIN(consign_time) mn, MAX(consign_time) mx, COUNT_BIG(*) n FROM dbo.dwd_wdt_stockout_sales'
))
print('stockin created:', db.fetch_one(
    'SELECT MIN(created_time) mn, MAX(created_time) mx, COUNT_BIG(*) n FROM dbo.dwd_wdt_stockin_refund'
))
print('BI result overall:', db.fetch_one(
    'SELECT MIN(biz_date) mn, MAX(biz_date) mx, COUNT(*) n FROM BI_lqx.dbo.bi_suite_ship_performance_daily'
))

print('\n=== 该套组 BI 明细样例 ===')
for r in db.fetch_all("""
SELECT TOP 8 biz_date, shop_code, is_dabo, ship_order_cnt, ship_amount, refund_amount, net_amount
FROM BI_lqx.dbo.bi_suite_ship_performance_daily
WHERE suite_no = ?
ORDER BY biz_date, shop_code
""", (SUITE,)):
    print(r)

print('\n=== 2025-12 有无该套组发货 ===')
print(db.fetch_one("""
SELECT COUNT_BIG(*) n, SUM(CAST(d.share_amount AS DECIMAL(19,4))) ship
FROM dbo.dwd_wdt_stockout_sales h
JOIN dbo.dwd_wdt_stockout_sales_detail d ON d.stockout_id=h.stockout_id
WHERE LTRIM(RTRIM(d.suite_no))=? AND d.goods_type IN (0,1)
  AND h.consign_time >= '2025-12-01' AND h.consign_time < '2026-01-01'
""", (SUITE,)))
