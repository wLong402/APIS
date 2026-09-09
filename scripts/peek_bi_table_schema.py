import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager
db = get_db_manager()
print('cols:')
for c in db.fetch_all("""
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM BI_lqx.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME='bi_suite_ship_performance_daily'
ORDER BY ORDINAL_POSITION
"""):
    print(c)
print('pks/constraints:')
for r in db.fetch_all("""
SELECT kc.name, kc.type_desc
FROM BI_lqx.sys.key_constraints kc
WHERE kc.parent_object_id = OBJECT_ID(N'BI_lqx.dbo.bi_suite_ship_performance_daily')
UNION ALL
SELECT dc.name, 'DEFAULT'
FROM BI_lqx.sys.default_constraints dc
WHERE dc.parent_object_id = OBJECT_ID(N'BI_lqx.dbo.bi_suite_ship_performance_daily')
"""):
    print(r)
