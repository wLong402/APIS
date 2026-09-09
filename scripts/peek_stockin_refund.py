import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager
db = get_db_manager()

for label, date_col in [
    ('header.modified_time', 'h.modified_time'),
    ('detail.modified_time', 'd.modified_time'),
]:
    print(f'\n=== {label} by month ===')
    for r in db.fetch_all(f"""
    SELECT FORMAT(CAST({date_col} AS DATE), 'yyyy-MM') AS ym, COUNT_BIG(*) AS n
    FROM dbo.dwd_wdt_stockin_refund h
    INNER JOIN dbo.dwd_wdt_stockin_refund_detail d ON d.stockin_id = h.stockin_id
    WHERE {date_col} >= '2025-12-01'
    GROUP BY FORMAT(CAST({date_col} AS DATE), 'yyyy-MM')
    ORDER BY ym
    """):
        print(r)

print('\n=== map suite via stockout detail (all Jul) ===')
print(db.fetch_one("""
WITH refund_line AS (
    SELECT CAST(d.modified_time AS DATE) AS biz_date,
           LTRIM(RTRIM(sd.suite_no)) AS suite_no,
           d.stockin_id, d.spec_no, d.tid,
           MAX(CAST(d.actual_refund_amount AS DECIMAL(19,4))) AS refund_amount
    FROM dbo.dwd_wdt_stockin_refund h
    INNER JOIN dbo.dwd_wdt_stockin_refund_detail d ON d.stockin_id = h.stockin_id
    INNER JOIN dbo.dwd_wdt_stockout_sales_detail sd
        ON LTRIM(RTRIM(sd.src_tid)) = LTRIM(RTRIM(d.tid))
       AND LTRIM(RTRIM(sd.spec_no)) = LTRIM(RTRIM(d.spec_no))
       AND sd.goods_type IN (0, 1)
    WHERE CAST(d.modified_time AS DATE) BETWEEN '2026-07-01' AND '2026-07-10'
      AND sd.suite_no IS NOT NULL AND LTRIM(RTRIM(sd.suite_no)) <> N''
    GROUP BY CAST(d.modified_time AS DATE), LTRIM(RTRIM(sd.suite_no)), d.stockin_id, d.spec_no, d.tid
)
SELECT COUNT(*) AS rows, COUNT(DISTINCT suite_no) AS suites, SUM(refund_amount) AS amt FROM refund_line
"""))

print('\n=== map suite: detail first, wide fallback (Jul) ===')
print(db.fetch_one("""
WITH refund_src AS (
    SELECT CAST(d.modified_time AS DATE) AS biz_date,
           d.stockin_id, d.spec_no, d.tid,
           MAX(CAST(d.actual_refund_amount AS DECIMAL(19,4))) AS refund_amount
    FROM dbo.dwd_wdt_stockin_refund h
    INNER JOIN dbo.dwd_wdt_stockin_refund_detail d ON d.stockin_id = h.stockin_id
    WHERE CAST(d.modified_time AS DATE) BETWEEN '2026-07-01' AND '2026-07-10'
    GROUP BY CAST(d.modified_time AS DATE), d.stockin_id, d.spec_no, d.tid
),
refund_suite AS (
    SELECT r.biz_date, r.stockin_id, r.spec_no, r.tid, r.refund_amount,
           COALESCE(
               NULLIF(LTRIM(RTRIM(sd.suite_no)), N''),
               NULLIF(LTRIM(RTRIM(w.suite_no)), N'')
           ) AS suite_no
    FROM refund_src r
    LEFT JOIN dbo.dwd_wdt_stockout_sales_detail sd
        ON LTRIM(RTRIM(sd.src_tid)) = LTRIM(RTRIM(r.tid))
       AND LTRIM(RTRIM(sd.spec_no)) = LTRIM(RTRIM(r.spec_no))
       AND sd.goods_type IN (0, 1)
    LEFT JOIN dbo.dwd_wdt_stockout_sales_wide w
        ON w.rec_id IS NOT NULL
       AND LTRIM(RTRIM(w.src_tid)) = LTRIM(RTRIM(r.tid))
       AND LTRIM(RTRIM(w.spec_no)) = LTRIM(RTRIM(r.spec_no))
       AND w.goods_type IN (0, 1)
)
SELECT COUNT(*) AS rows,
       SUM(CASE WHEN suite_no IS NOT NULL THEN 1 ELSE 0 END) AS mapped,
       SUM(CASE WHEN suite_no IS NOT NULL THEN refund_amount ELSE 0 END) AS amt
FROM refund_suite
"""))

print('\n=== Dec same approach ===')
print(db.fetch_one("""
WITH refund_src AS (
    SELECT CAST(d.modified_time AS DATE) AS biz_date,
           d.stockin_id, d.spec_no, d.tid,
           MAX(CAST(d.actual_refund_amount AS DECIMAL(19,4))) AS refund_amount
    FROM dbo.dwd_wdt_stockin_refund h
    INNER JOIN dbo.dwd_wdt_stockin_refund_detail d ON d.stockin_id = h.stockin_id
    WHERE CAST(d.modified_time AS DATE) BETWEEN '2025-12-01' AND '2025-12-31'
    GROUP BY CAST(d.modified_time AS DATE), d.stockin_id, d.spec_no, d.tid
),
refund_suite AS (
    SELECT r.biz_date, r.refund_amount,
           COALESCE(NULLIF(LTRIM(RTRIM(sd.suite_no)), N''), NULLIF(LTRIM(RTRIM(w.suite_no)), N'')) AS suite_no
    FROM refund_src r
    LEFT JOIN dbo.dwd_wdt_stockout_sales_detail sd
        ON LTRIM(RTRIM(sd.src_tid)) = LTRIM(RTRIM(r.tid))
       AND LTRIM(RTRIM(sd.spec_no)) = LTRIM(RTRIM(r.spec_no)) AND sd.goods_type IN (0, 1)
    LEFT JOIN dbo.dwd_wdt_stockout_sales_wide w
        ON LTRIM(RTRIM(w.src_tid)) = LTRIM(RTRIM(r.tid))
       AND LTRIM(RTRIM(w.spec_no)) = LTRIM(RTRIM(r.spec_no)) AND w.goods_type IN (0, 1)
)
SELECT COUNT(*) AS rows,
       SUM(CASE WHEN suite_no IS NOT NULL THEN 1 ELSE 0 END) AS mapped,
       SUM(CASE WHEN suite_no IS NOT NULL THEN refund_amount ELSE 0 END) AS amt
FROM refund_suite
"""))
