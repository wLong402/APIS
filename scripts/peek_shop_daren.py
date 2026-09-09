import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager
db = get_db_manager()

print('distinct sn count:', db.fetch_one('SELECT COUNT(DISTINCT sn) n FROM BI_lqx.dbo.MR_daren WHERE sn IS NOT NULL AND LTRIM(RTRIM(sn))<>\'\''))
print('sn samples:', [r['sn'] for r in db.fetch_all('SELECT DISTINCT TOP 20 sn FROM BI_lqx.dbo.MR_daren WHERE sn IS NOT NULL')])

print('\nmatch suite prefix to sn:')
print(db.fetch_one("""
SELECT
  COUNT(DISTINCT g.suite_no) suites,
  SUM(CASE WHEN d.sn IS NOT NULL THEN 1 ELSE 0 END) matched
FROM BI_lqx.dbo.DIM_Goods_wdt g
LEFT JOIN (
  SELECT DISTINCT LTRIM(RTRIM(sn)) sn FROM BI_lqx.dbo.MR_daren
  WHERE sn IS NOT NULL AND LTRIM(RTRIM(sn)) <> ''
) d ON d.sn = LEFT(LTRIM(RTRIM(g.suite_no)), 6)
"""))

print('\nmatched suite examples:')
for r in db.fetch_all("""
SELECT TOP 5 g.suite_no, LEFT(LTRIM(RTRIM(g.suite_no)), 6) prefix, d.sn, d.sn_name
FROM BI_lqx.dbo.DIM_Goods_wdt g
INNER JOIN (
  SELECT DISTINCT LTRIM(RTRIM(sn)) sn, MAX(sn_name) sn_name
  FROM BI_lqx.dbo.MR_daren
  WHERE sn IS NOT NULL AND LTRIM(RTRIM(sn)) <> ''
  GROUP BY LTRIM(RTRIM(sn))
) d ON d.sn = LEFT(LTRIM(RTRIM(g.suite_no)), 6)
"""):
    print(r)

# existing result table columns
print('\ncurrent bi table cols:')
for c in db.fetch_all("""
SELECT COLUMN_NAME FROM BI_lqx.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME='bi_suite_ship_performance_daily' ORDER BY ORDINAL_POSITION
"""):
    print(c['COLUMN_NAME'])
