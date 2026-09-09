# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db_manager

db = get_db_manager()

views = ['wdt_goods', 'DIM_Goods_wdt', 'DIM_Goods_TZ', 'DIM_Goods_detail_wdt', 'DIM_Goods']
for name in views:
    print(f'\n=== BI_lqx.dbo.{name} ===')
    try:
        cols = db.fetch_all(
            "SELECT COLUMN_NAME, DATA_TYPE FROM BI_lqx.INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
            (name,),
        )
        if not cols:
            print('  (not found)')
            continue
        for c in cols:
            print(f"  {c['COLUMN_NAME']:30} {c['DATA_TYPE']}")
        rows = db.fetch_all(f"SELECT TOP 2 * FROM BI_lqx.dbo.[{name}]")
        if rows:
            print('  sample row 1:', {k: rows[0][k] for k in list(rows[0].keys())[:12]})
    except Exception as e:
        print('  ERR', e)

tables = ['dwd_wdt_stockout_sales_wide', 'dwd_wdt_stockout_sales_detail', 'dwd_wdt_stockin_refund_wide']
for t in tables:
    print(f'\n=== dwd.dbo.{t} ===')
    try:
        n = db.fetch_one(f"SELECT COUNT_BIG(*) AS n FROM dbo.[{t}]")
        print('  count:', list(n.values())[0])
        cols = db.fetch_all(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME=? ORDER BY ORDINAL_POSITION",
            (t,),
        )
        names = [c['COLUMN_NAME'] for c in cols]
        keys = ['spec', 'goods', 'suite', 'suit', 'tz', 'qty', 'amount', 'time', 'date', 'stock', 'rec_id', 'price', 'cost']
        interesting = [x for x in names if any(k in x.lower() for k in keys)]
        print('  cols match:', interesting)
        row = db.fetch_one(f"SELECT TOP 1 * FROM dbo.[{t}]")
        if row:
            print('  sample:', {k: row[k] for k in list(row.keys())[:10]})
    except Exception as e:
        print('  ERR', e)

# search wdt_goods exact
print('\n=== search wdt_goods ===')
for r in db.fetch_all(
    "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM BI_lqx.INFORMATION_SCHEMA.TABLES "
    "WHERE TABLE_NAME = 'wdt_goods' OR TABLE_NAME LIKE '%wdt%goods%'"
):
    print(r)
