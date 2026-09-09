import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager
db = get_db_manager()

print('jul window join count:')
print(db.fetch_one("""
SELECT COUNT_BIG(*) AS n
FROM dbo.dwd_wdt_stockout_sales h
INNER JOIN dbo.dwd_wdt_stockout_sales_detail d ON d.stockout_id = h.stockout_id
WHERE CAST(h.consign_time AS DATE) BETWEEN '2026-07-07' AND '2026-07-10'
  AND d.suite_no IS NOT NULL AND LTRIM(RTRIM(d.suite_no)) <> N''
  AND d.goods_type IN (0, 1)
"""))

print('sample suite daily top 3:')
for r in db.fetch_all("""
SELECT TOP 3
    CAST(h.consign_time AS DATE) AS biz_date,
    d.suite_no,
    COUNT(DISTINCT h.stockout_id) AS orders,
    SUM(CAST(d.share_amount AS DECIMAL(19,4))) AS amt
FROM dbo.dwd_wdt_stockout_sales h
INNER JOIN dbo.dwd_wdt_stockout_sales_detail d ON d.stockout_id = h.stockout_id
WHERE CAST(h.consign_time AS DATE) BETWEEN '2026-07-07' AND '2026-07-10'
  AND d.suite_no IS NOT NULL AND LTRIM(RTRIM(d.suite_no)) <> N''
  AND d.goods_type IN (0, 1)
GROUP BY CAST(h.consign_time AS DATE), d.suite_no
ORDER BY amt DESC
"""):
    print(r)
