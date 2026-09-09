# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db_manager

db = get_db_manager()

# stockout wide all columns
cols = db.fetch_all(
    "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='dwd_wdt_stockout_sales_wide' ORDER BY ORDINAL_POSITION"
)
print('dwd_wdt_stockout_sales_wide columns:')
for c in cols:
    print(f"  {c['COLUMN_NAME']:35} {c['DATA_TYPE']}")

# goods_type and suite distribution
print('\n=== goods_type / suite_no stats ===')
for r in db.fetch_all("""
SELECT TOP 20
    goods_type,
    CASE WHEN suite_no IS NULL OR LTRIM(RTRIM(suite_no)) = '' THEN 0 ELSE 1 END AS has_suite,
    COUNT_BIG(*) AS cnt
FROM dbo.dwd_wdt_stockout_sales_wide
GROUP BY goods_type, CASE WHEN suite_no IS NULL OR LTRIM(RTRIM(suite_no)) = '' THEN 0 ELSE 1 END
ORDER BY cnt DESC
"""):
    print(r)

# sample suite shipment
print('\n=== same stockout_id suite lines ===')
row = db.fetch_one("""
SELECT TOP 1 stockout_id FROM dbo.dwd_wdt_stockout_sales_wide
WHERE suite_no IS NOT NULL AND LTRIM(RTRIM(suite_no)) <> ''
GROUP BY stockout_id HAVING COUNT(*) > 1
""")
if row:
    sid = row['stockout_id']
    lines = db.fetch_all("""
    SELECT goods_type, suite_no, suite_num, spec_no, goods_no, num, total_amount, share_amount, consign_time
    FROM dbo.dwd_wdt_stockout_sales_wide WHERE stockout_id = ?
    """, (sid,))
    print('stockout_id', sid, 'lines', len(lines))
    for ln in lines:
        print(ln)

print('\n=== goods_type stats (with suite_no) since 2026-04 ===')
for r in db.fetch_all("""
SELECT goods_type, COUNT_BIG(*) AS n,
  SUM(CAST(num AS DECIMAL(19,4))) AS sum_num,
  SUM(CAST(suite_num AS DECIMAL(19,4))) AS sum_suite_num,
  SUM(CAST(share_amount AS DECIMAL(19,4))) AS sum_share
FROM dbo.dwd_wdt_stockout_sales_wide
WHERE consign_time >= '2026-04-01'
  AND suite_no IS NOT NULL AND LTRIM(RTRIM(suite_no)) <> ''
GROUP BY goods_type
ORDER BY n DESC
"""):
    print(r)

print('\n=== per suite daily (goods_type=1) top 5 ===')
for r in db.fetch_all("""
SELECT TOP 5
    CAST(o.consign_time AS DATE) AS biz_date,
    g.suite_no,
    g.suite_name,
    COUNT(DISTINCT o.stockout_id) AS order_cnt,
    SUM(CAST(o.suite_num AS DECIMAL(19,4))) AS suite_qty,
    SUM(CAST(o.share_amount AS DECIMAL(19,4))) AS ship_amount
FROM dbo.dwd_wdt_stockout_sales_wide o
INNER JOIN BI_lqx.dbo.DIM_Goods_wdt g ON g.suite_no = o.suite_no
WHERE o.consign_time >= '2026-04-01' AND o.consign_time < '2026-04-08'
  AND o.goods_type = 1
GROUP BY CAST(o.consign_time AS DATE), g.suite_no, g.suite_name
ORDER BY ship_amount DESC
"""):
    print(r)

print('\n=== stockin sample ===')
for r in db.fetch_all("""
SELECT TOP 2 check_time, spec_no, goods_no, stockin_num, total_amount, refund_no
FROM dbo.dwd_wdt_stockin_refund_wide
WHERE check_time >= '2026-04-01'
ORDER BY check_time DESC
"""):
    print(r)

n = db.fetch_one('SELECT COUNT(*) AS n FROM BI_lqx.dbo.DIM_Goods_wdt')
print('\nDIM_Goods_wdt count:', list(n.values())[0])
