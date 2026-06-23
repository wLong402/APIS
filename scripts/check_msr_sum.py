# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from core.database import get_db_manager

db = get_db_manager()
t = 'wdt_marketing_share_result'
day = '2026-05-23'
target = Decimal('2177030.0030')


def q(sql, params=()):
    r = db.fetch_one(sql, params)
    return list(r.values())[0] if r else None


variants = [
    ('6811669 sum amount', f"SELECT SUM(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4))) FROM dbo.[{t}] WHERE eventday = ? AND project = '6811669'", (day,)),
    ('6811669 sum abs', f"SELECT SUM(ABS(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4)))) FROM dbo.[{t}] WHERE eventday = ? AND project = '6811669'", (day,)),
    ('6811669+6811668 sum abs', f"SELECT SUM(ABS(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4)))) FROM dbo.[{t}] WHERE eventday = ? AND project IN ('6811669','6811668')", (day,)),
    ('like 全域 sum abs', f"SELECT SUM(ABS(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4)))) FROM dbo.[{t}] WHERE eventday = ? AND projectname LIKE N'%全域%'", (day,)),
    ('6811669 negative abs only', f"SELECT SUM(ABS(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4)))) FROM dbo.[{t}] WHERE eventday = ? AND project='6811669' AND TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4)) < 0", (day,)),
    ('6811669 positive sum', f"SELECT SUM(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4))) FROM dbo.[{t}] WHERE eventday = ? AND project='6811669' AND TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4)) > 0", (day,)),
    ('6811669 DZSW074 sum abs', f"SELECT SUM(ABS(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4)))) FROM dbo.[{t}] WHERE eventday = ? AND project='6811669' AND shopno='DZSW074'", (day,)),
    ('6811669 DZSW244 sum abs', f"SELECT SUM(ABS(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4)))) FROM dbo.[{t}] WHERE eventday = ? AND project='6811669' AND shopno='DZSW244'", (day,)),
    ('direct cast sum', f"SELECT SUM(CAST(amount AS DECIMAL(19,4))) FROM dbo.[{t}] WHERE eventday = ? AND project='6811669'", (day,)),
    ('count', f"SELECT COUNT(*) FROM dbo.[{t}] WHERE eventday = ? AND project='6811669'", (day,)),
]

for name, sql, params in variants:
    v = q(sql, params)
    d = abs(Decimal(str(v or 0)) - target)
    print(f'{name}: {v}  diff={d}')

print('\n--- extra ---')
for day in ['2026-05-23', '2025-05-23']:
    r = db.fetch_one(
        f"SELECT COUNT(*) c, SUM(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4))) s, "
        f"SUM(ABS(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4)))) a "
        f"FROM dbo.[{t}] WHERE eventday = ? AND project = '6811669'",
        (day,),
    )
    a = list(r.values())[2] if r and list(r.values())[2] is not None else 0
    print(day, r, 'diff_abs', abs(Decimal(str(a)) - target))

r = db.fetch_one(
    f"SELECT COUNT(*) c, SUM(ABS(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4)))) a "
    f"FROM dbo.[{t}] WHERE eventday = '2026-05-23' AND project='6811669' "
    f"AND roomid IS NOT NULL AND LTRIM(RTRIM(roomid)) <> N''"
)
print('with roomid', r, 'diff', abs(Decimal(str(list(r.values())[1])) - target))

rows = db.fetch_all(
    f"SELECT incomeoutdirectionstr, COUNT(*) c, "
    f"SUM(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4))) s, "
    f"SUM(ABS(TRY_CAST(REPLACE(amount, ',', '') AS DECIMAL(19,4)))) a "
    f"FROM dbo.[{t}] WHERE eventday='2026-05-23' AND project='6811669' "
    f"GROUP BY incomeoutdirectionstr"
)
for x in rows:
    print('dir', x)

# compare API vs DB row-by-row sum on sample
from connectors.wdt.client import get_wdt_client
api = get_wdt_client().marketing_share_result_api
all_rows = api.query_all('2026-05-23', '2026-05-23', page_size=200)
live = [x for x in all_rows if str(x.get('project')) == '6811669']
api_sum = sum(float(x.get('amount') or 0) for x in live)
api_abs = sum(abs(float(x.get('amount') or 0)) for x in live)
print('api live count', len(live), 'sum', api_sum, 'abs', api_abs)
