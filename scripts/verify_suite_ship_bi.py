# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_manager

db = get_db_manager()
rows = db.fetch_all("""
SELECT TOP 8 biz_date, suite_no, LEFT(suite_name, 30) AS suite_name,
       ship_amount, refund_amount, net_amount
FROM dbo.bi_suite_ship_performance_daily
ORDER BY net_amount DESC
""")
for r in rows:
    print(r)
n = db.fetch_one("SELECT COUNT(*) AS n, COUNT(DISTINCT suite_no) AS suites FROM dbo.bi_suite_ship_performance_daily")
print('summary', n)
