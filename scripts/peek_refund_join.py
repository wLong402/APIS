import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager
db = get_db_manager()

print('wide matched vs unmatched refund dec')
print(db.fetch_one("""
SELECT
  SUM(CASE WHEN w.rec_id IS NOT NULL THEN 1 ELSE 0 END) AS matched,
  SUM(CASE WHEN w.rec_id IS NULL THEN 1 ELSE 0 END) AS unmatched,
  SUM(CASE WHEN w.rec_id IS NOT NULL THEN CAST(r.total_amount AS DECIMAL(19,4)) ELSE 0 END) AS matched_amt,
  SUM(CASE WHEN w.rec_id IS NULL THEN CAST(r.total_amount AS DECIMAL(19,4)) ELSE 0 END) AS unmatched_amt
FROM dbo.dwd_wdt_stockin_refund_wide r
LEFT JOIN dbo.dwd_wdt_stockout_sales_wide w
  ON LTRIM(RTRIM(w.src_tid)) = LTRIM(RTRIM(r.tid))
 AND LTRIM(RTRIM(w.spec_no)) = LTRIM(RTRIM(r.spec_no))
 AND w.goods_type IN (0, 1)
WHERE CAST(r.check_time AS DATE) BETWEEN '2025-12-01' AND '2025-12-31'
"""))

print('\ntrade_no sample vs refund tid')
print('refund', db.fetch_one("SELECT TOP 1 tid FROM dbo.dwd_wdt_stockin_refund_wide"))
print('header', db.fetch_one("SELECT TOP 1 trade_no, src_trade_no FROM dbo.dwd_wdt_stockout_sales WHERE trade_no IS NOT NULL"))

print('\nunmatched try header trade_no + detail')
print(db.fetch_one("""
SELECT COUNT_BIG(*) AS n
FROM dbo.dwd_wdt_stockin_refund_wide r
INNER JOIN dbo.dwd_wdt_stockout_sales h ON LTRIM(RTRIM(h.trade_no)) = LTRIM(RTRIM(r.tid))
INNER JOIN dbo.dwd_wdt_stockout_sales_detail d
  ON d.stockout_id = h.stockout_id AND LTRIM(RTRIM(d.spec_no)) = LTRIM(RTRIM(r.spec_no))
LEFT JOIN dbo.dwd_wdt_stockout_sales_wide w
  ON LTRIM(RTRIM(w.src_tid)) = LTRIM(RTRIM(r.tid))
 AND LTRIM(RTRIM(w.spec_no)) = LTRIM(RTRIM(r.spec_no))
WHERE CAST(r.check_time AS DATE) BETWEEN '2025-12-01' AND '2025-12-31'
  AND w.rec_id IS NULL
"""))

print('\nproposed refund daily dec total')
print(db.fetch_one("""
WITH refund_line AS (
    SELECT
        CAST(r.check_time AS DATE) AS biz_date,
        COALESCE(
            NULLIF(LTRIM(RTRIM(w.suite_no)), N''),
            NULLIF(LTRIM(RTRIM(d.suite_no)), N'')
        ) AS suite_no,
        CAST(r.total_amount AS DECIMAL(19, 4)) AS refund_amount
    FROM dbo.dwd_wdt_stockin_refund_wide r
    LEFT JOIN dbo.dwd_wdt_stockout_sales_wide w
        ON LTRIM(RTRIM(w.src_tid)) = LTRIM(RTRIM(r.tid))
       AND LTRIM(RTRIM(w.spec_no)) = LTRIM(RTRIM(r.spec_no))
       AND w.goods_type IN (0, 1)
    LEFT JOIN dbo.dwd_wdt_stockout_sales h
        ON LTRIM(RTRIM(h.trade_no)) = LTRIM(RTRIM(r.tid))
    LEFT JOIN dbo.dwd_wdt_stockout_sales_detail d
        ON d.stockout_id = h.stockout_id
       AND LTRIM(RTRIM(d.spec_no)) = LTRIM(RTRIM(r.spec_no))
       AND d.goods_type IN (0, 1)
    WHERE CAST(r.check_time AS DATE) BETWEEN '2025-12-01' AND '2025-12-31'
)
SELECT COUNT(*) AS mapped_rows,
       SUM(CASE WHEN suite_no IS NOT NULL THEN 1 ELSE 0 END) AS has_suite,
       SUM(CASE WHEN suite_no IS NOT NULL THEN refund_amount ELSE 0 END) AS amt
FROM refund_line
"""))
