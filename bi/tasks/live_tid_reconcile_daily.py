# -*- coding: utf-8 -*-
"""
示例：直播订单 tid 对账（按日汇总）

源表：dwd_check_live、dwd_wdt_profits_live_order
结果表：bi_live_tid_reconcile_daily（供 BI 报表直接查询）
"""

from bi.registry import register_task
from bi.task import BiTask

CREATE_TABLE_SQL = """
IF OBJECT_ID(N'dbo.bi_live_tid_reconcile_daily', N'U') IS NULL
CREATE TABLE dbo.bi_live_tid_reconcile_daily (
    biz_date DATE NOT NULL,
    chk_cnt INT NOT NULL DEFAULT 0,
    pull_cnt INT NOT NULL DEFAULT 0,
    matched_cnt INT NOT NULL DEFAULT 0,
    missing_cnt INT NOT NULL DEFAULT 0,
    extra_cnt INT NOT NULL DEFAULT 0,
    match_rate DECIMAL(9, 2) NULL,
    status_text NVARCHAR(32) NULL,
    computed_at DATETIME NOT NULL CONSTRAINT DF_bi_live_tid_reconcile_daily_computed_at DEFAULT (GETDATE()),
    CONSTRAINT PK_bi_live_tid_reconcile_daily PRIMARY KEY (biz_date)
);
"""


def _build_select_sql(start_date: str, end_date: str) -> str:
    return f"""
SELECT
    d.biz_date,
    ISNULL(cc.cnt, 0) AS chk_cnt,
    ISNULL(pc.cnt, 0) AS pull_cnt,
    ISNULL(m.cnt, 0) AS matched_cnt,
    ISNULL(ms.cnt, 0) AS missing_cnt,
    ISNULL(e.cnt, 0) AS extra_cnt,
    CAST(
        100.0 * ISNULL(m.cnt, 0) / NULLIF(ISNULL(cc.cnt, 0), 0)
        AS DECIMAL(9, 2)
    ) AS match_rate,
    CASE
        WHEN ISNULL(cc.cnt, 0) = 0 THEN N'基准无数据'
        WHEN ISNULL(ms.cnt, 0) > 0 THEN N'有漏单'
        ELSE N'正常'
    END AS status_text,
    GETDATE() AS computed_at
FROM (
    SELECT biz_date FROM (
        SELECT CAST(pay_date AS DATE) AS biz_date
        FROM dbo.dwd_check_live
        WHERE tid IS NOT NULL AND LTRIM(RTRIM(tid)) <> N''
          AND CAST(pay_date AS DATE) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY CAST(pay_date AS DATE)
    ) x
    UNION
    SELECT biz_date FROM (
        SELECT CAST(payTime AS DATE) AS biz_date
        FROM dbo.dwd_wdt_profits_live_order
        WHERE platOrderNo IS NOT NULL AND LTRIM(RTRIM(platOrderNo)) <> N''
          AND payTime IS NOT NULL
          AND CAST(payTime AS DATE) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY CAST(payTime AS DATE)
    ) y
) d
LEFT JOIN (
    SELECT CAST(pay_date AS DATE) AS biz_date, COUNT(*) AS cnt
    FROM (
        SELECT CAST(pay_date AS DATE) AS pay_date, LTRIM(RTRIM(tid)) AS tid
        FROM dbo.dwd_check_live
        WHERE tid IS NOT NULL AND LTRIM(RTRIM(tid)) <> N''
          AND CAST(pay_date AS DATE) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY CAST(pay_date AS DATE), LTRIM(RTRIM(tid))
    ) c
    GROUP BY CAST(pay_date AS DATE)
) cc ON cc.biz_date = d.biz_date
LEFT JOIN (
    SELECT CAST(payTime AS DATE) AS biz_date, COUNT(*) AS cnt
    FROM (
        SELECT CAST(payTime AS DATE) AS payTime, LTRIM(RTRIM(platOrderNo)) AS tid
        FROM dbo.dwd_wdt_profits_live_order
        WHERE platOrderNo IS NOT NULL AND LTRIM(RTRIM(platOrderNo)) <> N''
          AND payTime IS NOT NULL
          AND CAST(payTime AS DATE) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY CAST(payTime AS DATE), LTRIM(RTRIM(platOrderNo))
    ) p
    GROUP BY CAST(payTime AS DATE)
) pc ON pc.biz_date = d.biz_date
LEFT JOIN (
    SELECT c.biz_date, COUNT(*) AS cnt
    FROM (
        SELECT CAST(pay_date AS DATE) AS biz_date, LTRIM(RTRIM(tid)) AS tid
        FROM dbo.dwd_check_live
        WHERE tid IS NOT NULL AND LTRIM(RTRIM(tid)) <> N''
          AND CAST(pay_date AS DATE) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY CAST(pay_date AS DATE), LTRIM(RTRIM(tid))
    ) c
    INNER JOIN (
        SELECT CAST(payTime AS DATE) AS biz_date, LTRIM(RTRIM(platOrderNo)) AS tid
        FROM dbo.dwd_wdt_profits_live_order
        WHERE platOrderNo IS NOT NULL AND LTRIM(RTRIM(platOrderNo)) <> N''
          AND payTime IS NOT NULL
          AND CAST(payTime AS DATE) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY CAST(payTime AS DATE), LTRIM(RTRIM(platOrderNo))
    ) p ON c.biz_date = p.biz_date AND c.tid = p.tid
    GROUP BY c.biz_date
) m ON m.biz_date = d.biz_date
LEFT JOIN (
    SELECT c.biz_date, COUNT(*) AS cnt
    FROM (
        SELECT CAST(pay_date AS DATE) AS biz_date, LTRIM(RTRIM(tid)) AS tid
        FROM dbo.dwd_check_live
        WHERE tid IS NOT NULL AND LTRIM(RTRIM(tid)) <> N''
          AND CAST(pay_date AS DATE) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY CAST(pay_date AS DATE), LTRIM(RTRIM(tid))
    ) c
    LEFT JOIN (
        SELECT CAST(payTime AS DATE) AS biz_date, LTRIM(RTRIM(platOrderNo)) AS tid
        FROM dbo.dwd_wdt_profits_live_order
        WHERE platOrderNo IS NOT NULL AND LTRIM(RTRIM(platOrderNo)) <> N''
          AND payTime IS NOT NULL
          AND CAST(payTime AS DATE) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY CAST(payTime AS DATE), LTRIM(RTRIM(platOrderNo))
    ) p ON c.biz_date = p.biz_date AND c.tid = p.tid
    WHERE p.tid IS NULL
    GROUP BY c.biz_date
) ms ON ms.biz_date = d.biz_date
LEFT JOIN (
    SELECT p.biz_date, COUNT(*) AS cnt
    FROM (
        SELECT CAST(payTime AS DATE) AS biz_date, LTRIM(RTRIM(platOrderNo)) AS tid
        FROM dbo.dwd_wdt_profits_live_order
        WHERE platOrderNo IS NOT NULL AND LTRIM(RTRIM(platOrderNo)) <> N''
          AND payTime IS NOT NULL
          AND CAST(payTime AS DATE) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY CAST(payTime AS DATE), LTRIM(RTRIM(platOrderNo))
    ) p
    LEFT JOIN (
        SELECT CAST(pay_date AS DATE) AS biz_date, LTRIM(RTRIM(tid)) AS tid
        FROM dbo.dwd_check_live
        WHERE tid IS NOT NULL AND LTRIM(RTRIM(tid)) <> N''
          AND CAST(pay_date AS DATE) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY CAST(pay_date AS DATE), LTRIM(RTRIM(tid))
    ) c ON c.biz_date = p.biz_date AND c.tid = p.tid
    WHERE c.tid IS NULL
    GROUP BY p.biz_date
) e ON e.biz_date = d.biz_date
"""


register_task(BiTask(
    name='live_tid_reconcile_daily',
    label='直播漏单对账（按日）',
    description='dwd_check_live 与 dwd_wdt_profits_live_order 按 tid 对账，写入 bi_live_tid_reconcile_daily',
    target_table='bi_live_tid_reconcile_daily',
    date_column='biz_date',
    create_table_sql=CREATE_TABLE_SQL,
    build_select_sql=_build_select_sql,
))
