# -*- coding: utf-8 -*-
"""诊断 suite_ship 发货 vs 退货数据差异"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db_manager

db = get_db_manager()
START, END = '2026-07-01', '2026-07-10'

print('=== 1. 结果表 BI_lqx (近10天) ===')
try:
    r = db.fetch_one(f"""
    SELECT COUNT(*) AS n,
           SUM(CASE WHEN ship_amount <> 0 THEN 1 ELSE 0 END) AS ship_rows,
           SUM(CASE WHEN refund_amount <> 0 THEN 1 ELSE 0 END) AS refund_rows,
           SUM(CASE WHEN ship_amount = 0 AND refund_amount <> 0 THEN 1 ELSE 0 END) AS refund_only,
           SUM(CASE WHEN ship_amount <> 0 AND refund_amount = 0 THEN 1 ELSE 0 END) AS ship_only,
           SUM(ship_amount) AS sum_ship, SUM(refund_amount) AS sum_refund
    FROM BI_lqx.dbo.bi_suite_ship_performance_daily
    WHERE biz_date BETWEEN '{START}' AND '{END}'
    """)
    print(r)
    print('\nrefund_only sample:')
    for row in db.fetch_all(f"""
    SELECT TOP 5 biz_date, suite_no, ship_amount, refund_amount, net_amount
    FROM BI_lqx.dbo.bi_suite_ship_performance_daily
    WHERE biz_date BETWEEN '{START}' AND '{END}'
      AND ship_amount = 0 AND refund_amount <> 0
    ORDER BY refund_amount DESC
    """):
        print(row)
except Exception as e:
    print('BI_lqx table error:', e)

print('\n=== 2. 发货源: sales+detail (当前逻辑) ===')
print('detail columns:')
for c in db.fetch_all("""
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME='dwd_wdt_stockout_sales_detail'
  AND COLUMN_NAME IN ('suite_no','goods_type','share_amount','suite_num','spec_no','goods_no')
ORDER BY COLUMN_NAME
"""):
    print(' ', c['COLUMN_NAME'])

print('\ngoods_type + has_suite (detail join header):')
for r in db.fetch_all(f"""
SELECT d.goods_type,
       CASE WHEN d.suite_no IS NULL OR LTRIM(RTRIM(d.suite_no))='' THEN 0 ELSE 1 END AS has_suite,
       COUNT_BIG(*) AS n,
       SUM(CAST(d.share_amount AS DECIMAL(19,4))) AS sum_share
FROM dbo.dwd_wdt_stockout_sales h
INNER JOIN dbo.dwd_wdt_stockout_sales_detail d ON d.stockout_id = h.stockout_id
WHERE CAST(h.consign_time AS DATE) BETWEEN '{START}' AND '{END}'
GROUP BY d.goods_type,
         CASE WHEN d.suite_no IS NULL OR LTRIM(RTRIM(d.suite_no))='' THEN 0 ELSE 1 END
ORDER BY n DESC
"""):
    print(r)

print('\ncurrent filter goods_type IN (0,1) + suite_no:')
print(db.fetch_one(f"""
SELECT COUNT_BIG(*) AS n, SUM(CAST(d.share_amount AS DECIMAL(19,4))) AS sum_share
FROM dbo.dwd_wdt_stockout_sales h
INNER JOIN dbo.dwd_wdt_stockout_sales_detail d ON d.stockout_id = h.stockout_id
WHERE CAST(h.consign_time AS DATE) BETWEEN '{START}' AND '{END}'
  AND d.suite_no IS NOT NULL AND LTRIM(RTRIM(d.suite_no)) <> N''
  AND d.goods_type IN (0, 1)
"""))

print('\nwithout goods_type filter + suite_no:')
print(db.fetch_one(f"""
SELECT COUNT_BIG(*) AS n, SUM(CAST(d.share_amount AS DECIMAL(19,4))) AS sum_share
FROM dbo.dwd_wdt_stockout_sales h
INNER JOIN dbo.dwd_wdt_stockout_sales_detail d ON d.stockout_id = h.stockout_id
WHERE CAST(h.consign_time AS DATE) BETWEEN '{START}' AND '{END}'
  AND d.suite_no IS NOT NULL AND LTRIM(RTRIM(d.suite_no)) <> N''
"""))

print('\n=== 3. 发货源: sales_wide (旧逻辑) ===')
print(db.fetch_one(f"""
SELECT COUNT_BIG(*) AS n, SUM(CAST(share_amount AS DECIMAL(19,4))) AS sum_share,
       MAX(CAST(consign_time AS DATE)) AS max_date
FROM dbo.dwd_wdt_stockout_sales_wide
WHERE CAST(consign_time AS DATE) BETWEEN '{START}' AND '{END}'
  AND suite_no IS NOT NULL AND LTRIM(RTRIM(suite_no)) <> N''
  AND goods_type IN (0, 1)
"""))

print('\n=== 4. share_amount 是否为空 ===')
print(db.fetch_one(f"""
SELECT COUNT_BIG(*) AS n,
       SUM(CASE WHEN d.share_amount IS NULL OR d.share_amount = 0 THEN 1 ELSE 0 END) AS zero_share,
       SUM(CASE WHEN d.share_amount IS NOT NULL AND d.share_amount <> 0 THEN 1 ELSE 0 END) AS has_share
FROM dbo.dwd_wdt_stockout_sales h
INNER JOIN dbo.dwd_wdt_stockout_sales_detail d ON d.stockout_id = h.stockout_id
WHERE CAST(h.consign_time AS DATE) BETWEEN '{START}' AND '{END}'
  AND d.suite_no IS NOT NULL AND LTRIM(RTRIM(d.suite_no)) <> N''
  AND d.goods_type IN (0, 1)
"""))

print('\n=== 5. 样例 stockout_id (detail有suite但share=0) ===')
row = db.fetch_one(f"""
SELECT TOP 1 h.stockout_id
FROM dbo.dwd_wdt_stockout_sales h
INNER JOIN dbo.dwd_wdt_stockout_sales_detail d ON d.stockout_id = h.stockout_id
WHERE CAST(h.consign_time AS DATE) BETWEEN '{START}' AND '{END}'
  AND d.suite_no IS NOT NULL AND LTRIM(RTRIM(d.suite_no)) <> N''
  AND d.goods_type IN (0, 1)
  AND (d.share_amount IS NULL OR d.share_amount = 0)
""")
if row:
    sid = row['stockout_id']
    print('stockout_id', sid)
    for ln in db.fetch_all("""
    SELECT goods_type, suite_no, suite_num, spec_no, num, share_amount, total_amount, paid
    FROM dbo.dwd_wdt_stockout_sales_detail WHERE stockout_id = ?
    """, (sid,)):
        print(ln)
    wide = db.fetch_all("""
    SELECT goods_type, suite_no, suite_num, spec_no, num, share_amount, total_amount
    FROM dbo.dwd_wdt_stockout_sales_wide WHERE stockout_id = ?
    """, (sid,))
    print('wide lines', len(wide))
    for ln in wide[:5]:
        print(' wide', ln)

print('\n=== 6. BI 按月汇总 ===')
for r in db.fetch_all("""
SELECT FORMAT(biz_date, 'yyyy-MM') AS ym,
       COUNT(*) AS n,
       SUM(CASE WHEN ship_amount = 0 AND refund_amount <> 0 THEN 1 ELSE 0 END) AS refund_only,
       SUM(CASE WHEN ship_amount <> 0 THEN 1 ELSE 0 END) AS has_ship,
       SUM(ship_amount) AS ship,
       SUM(refund_amount) AS refund
FROM BI_lqx.dbo.bi_suite_ship_performance_daily
GROUP BY FORMAT(biz_date, 'yyyy-MM')
ORDER BY ym
"""):
    print(r)

print('\n=== 7. 退货源按月 ===')
for r in db.fetch_all("""
SELECT FORMAT(CAST(check_time AS DATE), 'yyyy-MM') AS ym,
       COUNT_BIG(*) AS n,
       SUM(CAST(total_amount AS DECIMAL(19,4))) AS amt
FROM dbo.dwd_wdt_stockin_refund_wide
WHERE check_time >= '2026-04-01'
GROUP BY FORMAT(CAST(check_time AS DATE), 'yyyy-MM')
ORDER BY ym
"""):
    print(r)

print('\n=== 8. wide 表最大日期 ===')
print(db.fetch_one('SELECT MAX(consign_time) AS mx, COUNT_BIG(*) AS n FROM dbo.dwd_wdt_stockout_sales_wide'))

print('\n=== 10. spec_no 一对多套组 ===')
print(db.fetch_one("""
SELECT COUNT(*) AS specs,
       SUM(CASE WHEN c > 1 THEN 1 ELSE 0 END) AS multi_suite_specs,
       MAX(c) AS max_suites
FROM (
    SELECT LTRIM(RTRIM(d.spec_no)) AS spec_no, COUNT(DISTINCT g.suite_no) AS c
    FROM BI_lqx.dbo.DIM_Goods_detail_wdt d
    JOIN BI_lqx.dbo.DIM_Goods_wdt g ON g.suite_id = d.suite_id
    WHERE d.spec_no IS NOT NULL AND LTRIM(RTRIM(d.spec_no)) <> N''
    GROUP BY LTRIM(RTRIM(d.spec_no))
) t
"""))

print('\n=== 11. 2025-12 退货源 vs join 后 ===')
print('raw:', db.fetch_one("""
SELECT COUNT_BIG(*) AS n, SUM(CAST(total_amount AS DECIMAL(19,4))) AS amt
FROM dbo.dwd_wdt_stockin_refund_wide
WHERE CAST(check_time AS DATE) BETWEEN '2025-12-01' AND '2025-12-31'
"""))
print('after item_suite join:', db.fetch_one("""
WITH item_suite AS (
    SELECT DISTINCT LTRIM(RTRIM(d.spec_no)) AS spec_no, g.suite_no
    FROM BI_lqx.dbo.DIM_Goods_detail_wdt d
    INNER JOIN BI_lqx.dbo.DIM_Goods_wdt g ON g.suite_id = d.suite_id
    WHERE d.spec_no IS NOT NULL AND LTRIM(RTRIM(d.spec_no)) <> N''
)
SELECT COUNT_BIG(*) AS n, SUM(CAST(r.total_amount AS DECIMAL(19,4))) AS amt
FROM dbo.dwd_wdt_stockin_refund_wide r
INNER JOIN item_suite m ON m.spec_no = LTRIM(RTRIM(r.spec_no))
WHERE CAST(r.check_time AS DATE) BETWEEN '2025-12-01' AND '2025-12-31'
"""))

print('\n=== 12. 2025-12 发货源 sales+detail ===')
print(db.fetch_one("""
SELECT COUNT_BIG(*) AS n, SUM(CAST(d.share_amount AS DECIMAL(19,4))) AS amt
FROM dbo.dwd_wdt_stockout_sales h
JOIN dbo.dwd_wdt_stockout_sales_detail d ON d.stockout_id = h.stockout_id
WHERE CAST(h.consign_time AS DATE) BETWEEN '2025-12-01' AND '2025-12-31'
  AND d.suite_no IS NOT NULL AND LTRIM(RTRIM(d.suite_no)) <> N''
  AND d.goods_type IN (0, 1)
"""))

print('\n=== 13. refund_wide 日期范围 ===')
print(db.fetch_one(
    'SELECT MIN(check_time) AS mn, MAX(check_time) AS mx, COUNT_BIG(*) AS n '
    'FROM dbo.dwd_wdt_stockin_refund_wide'
))

print('\n=== 14. 样例: 一对多 spec 导致退货翻倍 ===')
for r in db.fetch_all("""
SELECT TOP 3 spec_no, COUNT(DISTINCT suite_no) AS suite_cnt
FROM (
    SELECT LTRIM(RTRIM(d.spec_no)) AS spec_no, g.suite_no
    FROM BI_lqx.dbo.DIM_Goods_detail_wdt d
    JOIN BI_lqx.dbo.DIM_Goods_wdt g ON g.suite_id = d.suite_id
    WHERE d.spec_no IS NOT NULL AND LTRIM(RTRIM(d.spec_no)) <> N''
) x
GROUP BY spec_no
HAVING COUNT(DISTINCT suite_no) > 1
ORDER BY suite_cnt DESC
"""):
    print(r)

