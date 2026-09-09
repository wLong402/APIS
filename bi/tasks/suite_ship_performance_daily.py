# -*- coding: utf-8 -*-
"""
套组发货业绩（按日）

维表：BI_lqx.dbo.DIM_Goods_wdt（套组主数据）
发货：dwd.dbo.dwd_wdt_stockout_sales + dwd_wdt_stockout_sales_detail
退货：dwd.dbo.dwd_wdt_stockin_refund（created_time）+ dwd_wdt_stockin_refund_detail
粒度：biz_date + suite_no + shop_code（同日同套组不同店铺分行）
达播：suite_no 前 6 位命中 BI_lqx.dbo.MR_daren.sn，或 suite_no 以 DB0000 开头
结果表：BI_lqx.dbo.bi_suite_ship_performance_daily

实现：临时表 + 索引（GO 分批），不用 CTE。
"""

from datetime import datetime, timedelta

from bi.registry import register_task
from bi.task import BiTask

CREATE_TABLE_SQL = """
IF OBJECT_ID(N'BI_lqx.dbo.bi_suite_ship_performance_daily', N'U') IS NULL
CREATE TABLE BI_lqx.dbo.bi_suite_ship_performance_daily (
    biz_date DATE NOT NULL,
    suite_no NVARCHAR(64) NOT NULL,
    shop_code NVARCHAR(64) NOT NULL,
    suite_name NVARCHAR(256) NULL,
    is_dabo NVARCHAR(2) NOT NULL CONSTRAINT DF_bi_suite_ship_perf_is_dabo DEFAULT (N'否'),
    ship_order_cnt INT NOT NULL DEFAULT 0,
    ship_suite_qty DECIMAL(19, 4) NOT NULL DEFAULT 0,
    ship_amount DECIMAL(19, 4) NOT NULL DEFAULT 0,
    refund_amount DECIMAL(19, 4) NOT NULL DEFAULT 0,
    net_amount DECIMAL(19, 4) NOT NULL DEFAULT 0,
    computed_at DATETIME NOT NULL CONSTRAINT DF_bi_suite_ship_perf_computed_at DEFAULT (GETDATE()),
    CONSTRAINT PK_bi_suite_ship_performance_daily PRIMARY KEY (biz_date, suite_no, shop_code)
);
"""

MIGRATE_SQL = """
IF OBJECT_ID(N'BI_lqx.dbo.bi_suite_ship_performance_daily', N'U') IS NULL
BEGIN
    CREATE TABLE BI_lqx.dbo.bi_suite_ship_performance_daily (
        biz_date DATE NOT NULL,
        suite_no NVARCHAR(64) NOT NULL,
        shop_code NVARCHAR(64) NOT NULL,
        suite_name NVARCHAR(256) NULL,
        is_dabo NVARCHAR(2) NOT NULL CONSTRAINT DF_bi_suite_ship_perf_is_dabo DEFAULT (N'否'),
        ship_order_cnt INT NOT NULL DEFAULT 0,
        ship_suite_qty DECIMAL(19, 4) NOT NULL DEFAULT 0,
        ship_amount DECIMAL(19, 4) NOT NULL DEFAULT 0,
        refund_amount DECIMAL(19, 4) NOT NULL DEFAULT 0,
        net_amount DECIMAL(19, 4) NOT NULL DEFAULT 0,
        computed_at DATETIME NOT NULL CONSTRAINT DF_bi_suite_ship_perf_computed_at DEFAULT (GETDATE()),
        CONSTRAINT PK_bi_suite_ship_performance_daily PRIMARY KEY (biz_date, suite_no, shop_code)
    );
END
ELSE IF COL_LENGTH(N'BI_lqx.dbo.bi_suite_ship_performance_daily', 'shop_code') IS NULL
BEGIN
    DROP TABLE BI_lqx.dbo.bi_suite_ship_performance_daily;
    CREATE TABLE BI_lqx.dbo.bi_suite_ship_performance_daily (
        biz_date DATE NOT NULL,
        suite_no NVARCHAR(64) NOT NULL,
        shop_code NVARCHAR(64) NOT NULL,
        suite_name NVARCHAR(256) NULL,
        is_dabo NVARCHAR(2) NOT NULL CONSTRAINT DF_bi_suite_ship_perf_is_dabo DEFAULT (N'否'),
        ship_order_cnt INT NOT NULL DEFAULT 0,
        ship_suite_qty DECIMAL(19, 4) NOT NULL DEFAULT 0,
        ship_amount DECIMAL(19, 4) NOT NULL DEFAULT 0,
        refund_amount DECIMAL(19, 4) NOT NULL DEFAULT 0,
        net_amount DECIMAL(19, 4) NOT NULL DEFAULT 0,
        computed_at DATETIME NOT NULL CONSTRAINT DF_bi_suite_ship_perf_computed_at DEFAULT (GETDATE()),
        CONSTRAINT PK_bi_suite_ship_performance_daily PRIMARY KEY (biz_date, suite_no, shop_code)
    );
END
ELSE IF COL_LENGTH(N'BI_lqx.dbo.bi_suite_ship_performance_daily', 'is_dabo') IS NULL
BEGIN
    ALTER TABLE BI_lqx.dbo.bi_suite_ship_performance_daily
        ADD is_dabo NVARCHAR(2) NOT NULL DEFAULT (N'否');
END
ELSE IF EXISTS (
    SELECT 1
    FROM BI_lqx.INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = N'bi_suite_ship_performance_daily'
      AND COLUMN_NAME = N'is_dabo'
      AND DATA_TYPE = N'tinyint'
)
BEGIN
    DROP TABLE BI_lqx.dbo.bi_suite_ship_performance_daily;
    CREATE TABLE BI_lqx.dbo.bi_suite_ship_performance_daily (
        biz_date DATE NOT NULL,
        suite_no NVARCHAR(64) NOT NULL,
        shop_code NVARCHAR(64) NOT NULL,
        suite_name NVARCHAR(256) NULL,
        is_dabo NVARCHAR(2) NOT NULL CONSTRAINT DF_bi_suite_ship_perf_is_dabo DEFAULT (N'否'),
        ship_order_cnt INT NOT NULL DEFAULT 0,
        ship_suite_qty DECIMAL(19, 4) NOT NULL DEFAULT 0,
        ship_amount DECIMAL(19, 4) NOT NULL DEFAULT 0,
        refund_amount DECIMAL(19, 4) NOT NULL DEFAULT 0,
        net_amount DECIMAL(19, 4) NOT NULL DEFAULT 0,
        computed_at DATETIME NOT NULL CONSTRAINT DF_bi_suite_ship_perf_computed_at DEFAULT (GETDATE()),
        CONSTRAINT PK_bi_suite_ship_performance_daily PRIMARY KEY (biz_date, suite_no, shop_code)
    );
END
"""


def _next_day(ymd: str) -> str:
    return (datetime.strptime(ymd, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')


def _build_batch_sql(start_date: str, end_date: str, table_ref: str) -> str:
    end_excl = _next_day(end_date)
    return f"""
{MIGRATE_SQL}
GO
IF OBJECT_ID('tempdb..#ship_order') IS NOT NULL DROP TABLE #ship_order
GO
IF OBJECT_ID('tempdb..#ship_daily') IS NOT NULL DROP TABLE #ship_daily
GO
IF OBJECT_ID('tempdb..#refund_src') IS NOT NULL DROP TABLE #refund_src
GO
IF OBJECT_ID('tempdb..#refund_key') IS NOT NULL DROP TABLE #refund_key
GO
IF OBJECT_ID('tempdb..#suite_map') IS NOT NULL DROP TABLE #suite_map
GO
IF OBJECT_ID('tempdb..#refund_line') IS NOT NULL DROP TABLE #refund_line
GO
IF OBJECT_ID('tempdb..#refund_daily') IS NOT NULL DROP TABLE #refund_daily
GO
IF OBJECT_ID('tempdb..#suite_dim') IS NOT NULL DROP TABLE #suite_dim
GO
IF OBJECT_ID('tempdb..#daren_sn') IS NOT NULL DROP TABLE #daren_sn
GO
IF OBJECT_ID('tempdb..#keys') IS NOT NULL DROP TABLE #keys
GO
SELECT
    CAST(h.consign_time AS DATE) biz_date,
    LTRIM(RTRIM(d.suite_no)) suite_no,
    ISNULL(NULLIF(LTRIM(RTRIM(h.shop_no)), N''), N'') shop_code,
    h.stockout_id,
    MAX(CAST(d.suite_num AS DECIMAL(19, 4))) suite_qty,
    SUM(CAST(d.share_amount AS DECIMAL(19, 4))) suite_amount
INTO #ship_order
FROM dbo.dwd_wdt_stockout_sales h
INNER JOIN dbo.dwd_wdt_stockout_sales_detail d ON d.stockout_id = h.stockout_id
WHERE h.consign_time >= '{start_date}'
  AND h.consign_time < '{end_excl}'
  AND d.suite_no IS NOT NULL AND LTRIM(RTRIM(d.suite_no)) <> N''
  AND d.goods_type IN (0, 1)
GROUP BY CAST(h.consign_time AS DATE), LTRIM(RTRIM(d.suite_no)),
         ISNULL(NULLIF(LTRIM(RTRIM(h.shop_no)), N''), N''), h.stockout_id
GO
CREATE CLUSTERED INDEX IX_ship_order ON #ship_order (biz_date, suite_no, shop_code)
GO
SELECT
    biz_date,
    suite_no,
    shop_code,
    COUNT(*) ship_order_cnt,
    SUM(suite_qty) ship_suite_qty,
    SUM(suite_amount) ship_amount
INTO #ship_daily
FROM #ship_order
GROUP BY biz_date, suite_no, shop_code
GO
CREATE UNIQUE CLUSTERED INDEX IX_ship_daily ON #ship_daily (biz_date, suite_no, shop_code)
GO
SELECT
    CAST(h.created_time AS DATE) biz_date,
    d.stockin_id,
    ISNULL(NULLIF(LTRIM(RTRIM(h.shop_no)), N''), N'') shop_code,
    LTRIM(RTRIM(d.spec_no)) spec_no,
    LTRIM(RTRIM(d.tid)) tid,
    MAX(CAST(d.actual_refund_amount AS DECIMAL(19, 4))) refund_amount
INTO #refund_src
FROM dbo.dwd_wdt_stockin_refund h
INNER JOIN dbo.dwd_wdt_stockin_refund_detail d ON d.stockin_id = h.stockin_id
WHERE h.created_time >= '{start_date}'
  AND h.created_time < '{end_excl}'
  AND d.spec_no IS NOT NULL AND LTRIM(RTRIM(d.spec_no)) <> N''
  AND d.tid IS NOT NULL AND LTRIM(RTRIM(d.tid)) <> N''
GROUP BY CAST(h.created_time AS DATE), d.stockin_id,
         ISNULL(NULLIF(LTRIM(RTRIM(h.shop_no)), N''), N''),
         LTRIM(RTRIM(d.spec_no)), LTRIM(RTRIM(d.tid))
GO
CREATE CLUSTERED INDEX IX_refund_src ON #refund_src (tid, spec_no)
GO
SELECT DISTINCT tid, spec_no
INTO #refund_key
FROM #refund_src
GO
CREATE UNIQUE CLUSTERED INDEX IX_refund_key ON #refund_key (tid, spec_no)
GO
SELECT
    k.tid,
    k.spec_no,
    MIN(NULLIF(LTRIM(RTRIM(sd.suite_no)), N'')) suite_no
INTO #suite_map
FROM #refund_key k
INNER JOIN dbo.dwd_wdt_stockout_sales_detail sd
    ON sd.src_tid = k.tid
   AND sd.spec_no = k.spec_no
   AND sd.goods_type IN (0, 1)
WHERE sd.suite_no IS NOT NULL AND LTRIM(RTRIM(sd.suite_no)) <> N''
GROUP BY k.tid, k.spec_no
HAVING MIN(NULLIF(LTRIM(RTRIM(sd.suite_no)), N'')) IS NOT NULL
GO
INSERT INTO #suite_map (tid, spec_no, suite_no)
SELECT
    k.tid,
    k.spec_no,
    MIN(NULLIF(LTRIM(RTRIM(w.suite_no)), N''))
FROM #refund_key k
INNER JOIN dbo.dwd_wdt_stockout_sales_wide w
    ON w.src_tid = k.tid
   AND w.spec_no = k.spec_no
   AND w.goods_type IN (0, 1)
WHERE w.suite_no IS NOT NULL AND LTRIM(RTRIM(w.suite_no)) <> N''
  AND NOT EXISTS (
      SELECT 1 FROM #suite_map m WHERE m.tid = k.tid AND m.spec_no = k.spec_no
  )
GROUP BY k.tid, k.spec_no
HAVING MIN(NULLIF(LTRIM(RTRIM(w.suite_no)), N'')) IS NOT NULL
GO
CREATE UNIQUE CLUSTERED INDEX IX_suite_map ON #suite_map (tid, spec_no)
GO
SELECT
    r.biz_date,
    m.suite_no,
    r.shop_code,
    r.stockin_id,
    r.spec_no,
    r.tid,
    r.refund_amount
INTO #refund_line
FROM #refund_src r
INNER JOIN #suite_map m ON m.tid = r.tid AND m.spec_no = r.spec_no
GO
CREATE CLUSTERED INDEX IX_refund_line ON #refund_line (biz_date, suite_no, shop_code)
GO
SELECT
    biz_date,
    suite_no,
    shop_code,
    SUM(refund_amount) refund_amount
INTO #refund_daily
FROM #refund_line
GROUP BY biz_date, suite_no, shop_code
GO
CREATE UNIQUE CLUSTERED INDEX IX_refund_daily ON #refund_daily (biz_date, suite_no, shop_code)
GO
SELECT suite_no, MAX(suite_name) suite_name
INTO #suite_dim
FROM BI_lqx.dbo.DIM_Goods_wdt
GROUP BY suite_no
GO
CREATE UNIQUE CLUSTERED INDEX IX_suite_dim ON #suite_dim (suite_no)
GO
SELECT DISTINCT LTRIM(RTRIM(sn)) sn
INTO #daren_sn
FROM BI_lqx.dbo.MR_daren
WHERE sn IS NOT NULL AND LTRIM(RTRIM(sn)) <> N''
GO
CREATE UNIQUE CLUSTERED INDEX IX_daren_sn ON #daren_sn (sn)
GO
SELECT biz_date, suite_no, shop_code
INTO #keys
FROM #ship_daily
UNION
SELECT biz_date, suite_no, shop_code
FROM #refund_daily
GO
CREATE UNIQUE CLUSTERED INDEX IX_keys ON #keys (biz_date, suite_no, shop_code)
GO
INSERT INTO {table_ref} (
    biz_date, suite_no, shop_code, suite_name, is_dabo,
    ship_order_cnt, ship_suite_qty, ship_amount,
    refund_amount, net_amount, computed_at
)
SELECT
    k.biz_date,
    k.suite_no,
    k.shop_code,
    g.suite_name,
    CASE WHEN dn.sn IS NOT NULL OR LEFT(k.suite_no, 6) = N'DB0000' THEN N'是' ELSE N'否' END,
    ISNULL(s.ship_order_cnt, 0),
    ISNULL(s.ship_suite_qty, 0),
    ISNULL(s.ship_amount, 0),
    ISNULL(r.refund_amount, 0),
    ISNULL(s.ship_amount, 0) - ISNULL(r.refund_amount, 0),
    GETDATE()
FROM #keys k
INNER JOIN #suite_dim g ON g.suite_no = k.suite_no
LEFT JOIN #daren_sn dn ON dn.sn = LEFT(k.suite_no, 6)
LEFT JOIN #ship_daily s
    ON s.biz_date = k.biz_date AND s.suite_no = k.suite_no AND s.shop_code = k.shop_code
LEFT JOIN #refund_daily r
    ON r.biz_date = k.biz_date AND r.suite_no = k.suite_no AND r.shop_code = k.shop_code
"""


register_task(BiTask(
    name='suite_ship_performance_daily',
    label='套组发货业绩（按日）',
    description='按日+套组+店铺汇总净业绩；suite_no前6位命中MR_daren.sn或DB0000开头为达播',
    target_table='bi_suite_ship_performance_daily',
    date_column='biz_date',
    create_table_sql=CREATE_TABLE_SQL,
    target_database='BI_lqx',
    build_batch_sql=_build_batch_sql,
))
