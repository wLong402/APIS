/*
  直播正向订单漏数核对（按日期汇总）
  基准表: dbo.dwd_check_live
  目标表: dbo.dwd_wdt_profits_live_order   ← 核对拉取结果用 DWD，不用 ODS wdt_profits_live_order

  匹配: dwd_check_live.tid = dwd_wdt_profits_live_order.platOrderNo
  日期: dwd_check_live.pay_date = dwd_wdt_profits_live_order.payTime（按日）
  修改 @start_date / @end_date 后执行第 1 段
*/

DECLARE @start_date DATE = '2026-04-18';  -- profits_live_order 最早有数约从此日起
DECLARE @end_date   DATE = CAST(GETDATE() AS DATE);


-- ============================================================
-- 1) 【主查询】按日期汇总（中文表头）
-- ============================================================
WITH chk AS (
    SELECT
        CAST(pay_date AS DATE) AS biz_date,
        LTRIM(RTRIM(tid)) AS tid
    FROM dbo.dwd_check_live
    WHERE tid IS NOT NULL
      AND LTRIM(RTRIM(tid)) <> N''
      AND CAST(pay_date AS DATE) BETWEEN @start_date AND @end_date
    GROUP BY CAST(pay_date AS DATE), LTRIM(RTRIM(tid))
),
pull AS (
    SELECT
        CAST(payTime AS DATE) AS biz_date,
        LTRIM(RTRIM(platOrderNo)) AS tid
    FROM dbo.dwd_wdt_profits_live_order
    WHERE platOrderNo IS NOT NULL
      AND LTRIM(RTRIM(platOrderNo)) <> N''
      AND payTime IS NOT NULL
      AND CAST(payTime AS DATE) BETWEEN @start_date AND @end_date
    GROUP BY CAST(payTime AS DATE), LTRIM(RTRIM(platOrderNo))
),
chk_cnt AS (
    SELECT biz_date, COUNT(*) AS cnt FROM chk GROUP BY biz_date
),
pull_cnt AS (
    SELECT biz_date, COUNT(*) AS cnt FROM pull GROUP BY biz_date
),
matched AS (
    SELECT c.biz_date, COUNT(*) AS cnt
    FROM chk c
    INNER JOIN pull p ON c.biz_date = p.biz_date AND c.tid = p.tid
    GROUP BY c.biz_date
),
missing AS (
    SELECT c.biz_date, COUNT(*) AS cnt
    FROM chk c
    LEFT JOIN pull p ON c.biz_date = p.biz_date AND c.tid = p.tid
    WHERE p.tid IS NULL
    GROUP BY c.biz_date
),
extra AS (
    SELECT p.biz_date, COUNT(*) AS cnt
    FROM pull p
    LEFT JOIN chk c ON c.biz_date = p.biz_date AND c.tid = p.tid
    WHERE c.tid IS NULL
    GROUP BY p.biz_date
),
days AS (
    SELECT biz_date FROM chk_cnt
    UNION
    SELECT biz_date FROM pull_cnt
)
SELECT
    d.biz_date                              AS [日期],
    ISNULL(cc.cnt, 0)                       AS [基准订单数],
    ISNULL(pc.cnt, 0)                       AS [目标表订单数],
    ISNULL(m.cnt, 0)                        AS [匹配数],
    ISNULL(ms.cnt, 0)                       AS [漏拉数],
    ISNULL(e.cnt, 0)                        AS [多拉数],
    CAST(
        100.0 * ISNULL(m.cnt, 0) / NULLIF(ISNULL(cc.cnt, 0), 0)
        AS DECIMAL(9, 2)
    )                                       AS [匹配率],
    CASE
        WHEN ISNULL(cc.cnt, 0) = 0 THEN N'基准无数据'
        WHEN ISNULL(ms.cnt, 0) > 0 THEN N'有漏单'
        ELSE N'正常'
    END                                     AS [状态]
FROM days d
LEFT JOIN chk_cnt cc ON cc.biz_date = d.biz_date
LEFT JOIN pull_cnt pc ON pc.biz_date = d.biz_date
LEFT JOIN matched m ON m.biz_date = d.biz_date
LEFT JOIN missing ms ON ms.biz_date = d.biz_date
LEFT JOIN extra e ON e.biz_date = d.biz_date
ORDER BY d.biz_date;


-- ============================================================
-- 2) 仅看有漏单的日期（中文表头）
-- ============================================================
WITH chk AS (
    SELECT CAST(pay_date AS DATE) AS biz_date, LTRIM(RTRIM(tid)) AS tid
    FROM dbo.dwd_check_live
    WHERE tid IS NOT NULL AND LTRIM(RTRIM(tid)) <> N''
      AND CAST(pay_date AS DATE) BETWEEN @start_date AND @end_date
    GROUP BY CAST(pay_date AS DATE), LTRIM(RTRIM(tid))
),
pull AS (
    SELECT CAST(payTime AS DATE) AS biz_date, LTRIM(RTRIM(platOrderNo)) AS tid
    FROM dbo.dwd_wdt_profits_live_order
    WHERE platOrderNo IS NOT NULL AND LTRIM(RTRIM(platOrderNo)) <> N''
      AND payTime IS NOT NULL
      AND CAST(payTime AS DATE) BETWEEN @start_date AND @end_date
    GROUP BY CAST(payTime AS DATE), LTRIM(RTRIM(platOrderNo))
),
missing AS (
    SELECT c.biz_date, COUNT(*) AS missing_cnt
    FROM chk c
    LEFT JOIN pull p ON c.biz_date = p.biz_date AND c.tid = p.tid
    WHERE p.tid IS NULL
    GROUP BY c.biz_date
)
SELECT
    biz_date    AS [日期],
    missing_cnt AS [漏拉数]
FROM missing
WHERE missing_cnt > 0
ORDER BY biz_date;


-- ============================================================
-- 3) 指定单日：漏掉的 tid 明细（改 @check_date）
-- ============================================================
DECLARE @check_date DATE = '2026-06-01';

WITH chk AS (
    SELECT DISTINCT LTRIM(RTRIM(tid)) AS tid
    FROM dbo.dwd_check_live
    WHERE CAST(pay_date AS DATE) = @check_date
      AND tid IS NOT NULL AND LTRIM(RTRIM(tid)) <> N''
),
pull AS (
    SELECT DISTINCT LTRIM(RTRIM(platOrderNo)) AS tid
    FROM dbo.dwd_wdt_profits_live_order
    WHERE CAST(payTime AS DATE) = @check_date
      AND platOrderNo IS NOT NULL AND LTRIM(RTRIM(platOrderNo)) <> N''
)
SELECT
    @check_date AS [日期],
    c.tid       AS [漏拉tid]
FROM chk c
LEFT JOIN pull p ON c.tid = p.tid
WHERE p.tid IS NULL
ORDER BY c.tid;


-- ============================================================
-- 4) 指定单日：漏单上下文（达人/场次/直播间）
-- ============================================================
SELECT
    CAST(c.pay_date AS DATE) AS [日期],
    c.tid                    AS [平台单号tid],
    c.oid                    AS [子单号oid],
    c.influencer_id          AS [达人ID],
    c.live_salesman          AS [直播业务员],
    c.session_id             AS [场次ID],
    c.session_no             AS [场次编号],
    c.live_room_id           AS [直播间ID],
    c.live_order_type        AS [直播订单类型],
    c.order_channel          AS [订单渠道],
    c.team                   AS [团队],
    c.traffic_type           AS [流量类型],
    c.zb_type                AS [直播类型]
FROM dbo.dwd_check_live c
WHERE CAST(c.pay_date AS DATE) = @check_date
  AND c.tid IS NOT NULL AND LTRIM(RTRIM(c.tid)) <> N''
  AND NOT EXISTS (
      SELECT 1
      FROM dbo.dwd_wdt_profits_live_order p
      WHERE CAST(p.payTime AS DATE) = @check_date
        AND LTRIM(RTRIM(p.platOrderNo)) = LTRIM(RTRIM(c.tid))
  )
ORDER BY c.tid, c.oid;


-- ============================================================
-- 5) 【不按日期】仅按 tid 全量汇总（中文表头）
--    匹配: dwd_check_live.tid = dwd_wdt_profits_live_order.platOrderNo
--    不限制 pay_date / payTime 是否同一天
-- ============================================================
WITH chk AS (
    SELECT DISTINCT LTRIM(RTRIM(tid)) AS tid
    FROM dbo.dwd_check_live
    WHERE tid IS NOT NULL AND LTRIM(RTRIM(tid)) <> N''
),
pull AS (
    SELECT DISTINCT LTRIM(RTRIM(platOrderNo)) AS tid
    FROM dbo.dwd_wdt_profits_live_order
    WHERE platOrderNo IS NOT NULL AND LTRIM(RTRIM(platOrderNo)) <> N''
)
SELECT
    (SELECT COUNT(*) FROM chk) AS [基准订单数],
    (SELECT COUNT(*) FROM pull) AS [目标表订单数],
    (SELECT COUNT(*) FROM chk c INNER JOIN pull p ON c.tid = p.tid) AS [匹配数],
    (SELECT COUNT(*) FROM chk c LEFT JOIN pull p ON c.tid = p.tid WHERE p.tid IS NULL) AS [漏拉数],
    (SELECT COUNT(*) FROM pull p LEFT JOIN chk c ON c.tid = p.tid WHERE c.tid IS NULL) AS [多拉数],
    CAST(
        100.0 * (SELECT COUNT(*) FROM chk c INNER JOIN pull p ON c.tid = p.tid)
        / NULLIF((SELECT COUNT(*) FROM chk), 0)
        AS DECIMAL(9, 2)
    ) AS [匹配率];


-- ============================================================
-- 6) 【不按日期】基准有、目标表无的 tid 明细（带基准侧支付日期供参考）
-- ============================================================
WITH chk AS (
    SELECT DISTINCT LTRIM(RTRIM(tid)) AS tid
    FROM dbo.dwd_check_live
    WHERE tid IS NOT NULL AND LTRIM(RTRIM(tid)) <> N''
),
pull AS (
    SELECT DISTINCT LTRIM(RTRIM(platOrderNo)) AS tid
    FROM dbo.dwd_wdt_profits_live_order
    WHERE platOrderNo IS NOT NULL AND LTRIM(RTRIM(platOrderNo)) <> N''
),
missing AS (
    SELECT c.tid
    FROM chk c
    LEFT JOIN pull p ON c.tid = p.tid
    WHERE p.tid IS NULL
)
SELECT
    m.tid                           AS [漏拉tid],
    MIN(CAST(c.pay_date AS DATE))   AS [基准最早支付日],
    MAX(CAST(c.pay_date AS DATE))   AS [基准最晚支付日],
    COUNT(DISTINCT CAST(c.pay_date AS DATE)) AS [基准出现天数]
FROM missing m
INNER JOIN dbo.dwd_check_live c
    ON LTRIM(RTRIM(c.tid)) = m.tid
GROUP BY m.tid
ORDER BY m.tid;


-- ============================================================
-- 5) 【不按日期】仅按 tid 全量汇总（中文表头）
--    匹配: dwd_check_live.tid = dwd_wdt_profits_live_order.platOrderNo
--    不限制 pay_date / payTime 是否同一天
-- ============================================================
WITH chk AS (
    SELECT DISTINCT LTRIM(RTRIM(tid)) AS tid
    FROM dbo.dwd_check_live
    WHERE tid IS NOT NULL AND LTRIM(RTRIM(tid)) <> N''
),
pull AS (
    SELECT DISTINCT LTRIM(RTRIM(platOrderNo)) AS tid
    FROM dbo.dwd_wdt_profits_live_order
    WHERE platOrderNo IS NOT NULL AND LTRIM(RTRIM(platOrderNo)) <> N''
)
SELECT
    (SELECT COUNT(*) FROM chk) AS [基准订单数],
    (SELECT COUNT(*) FROM pull) AS [目标表订单数],
    (SELECT COUNT(*) FROM chk c INNER JOIN pull p ON c.tid = p.tid) AS [匹配数],
    (SELECT COUNT(*) FROM chk c LEFT JOIN pull p ON c.tid = p.tid WHERE p.tid IS NULL) AS [漏拉数],
    (SELECT COUNT(*) FROM pull p LEFT JOIN chk c ON c.tid = p.tid WHERE c.tid IS NULL) AS [多拉数],
    CAST(
        100.0 * (SELECT COUNT(*) FROM chk c INNER JOIN pull p ON c.tid = p.tid)
        / NULLIF((SELECT COUNT(*) FROM chk), 0)
        AS DECIMAL(9, 2)
    ) AS [匹配率];


-- ============================================================
-- 6) 【不按日期】基准有、目标表无的 tid 明细（带基准侧支付日期供参考）
-- ============================================================
WITH chk AS (
    SELECT DISTINCT LTRIM(RTRIM(tid)) AS tid
    FROM dbo.dwd_check_live
    WHERE tid IS NOT NULL AND LTRIM(RTRIM(tid)) <> N''
),
pull AS (
    SELECT DISTINCT LTRIM(RTRIM(platOrderNo)) AS tid
    FROM dbo.dwd_wdt_profits_live_order
    WHERE platOrderNo IS NOT NULL AND LTRIM(RTRIM(platOrderNo)) <> N''
),
missing AS (
    SELECT c.tid
    FROM chk c
    LEFT JOIN pull p ON c.tid = p.tid
    WHERE p.tid IS NULL
)
SELECT
    m.tid                           AS [漏拉tid],
    MIN(CAST(c.pay_date AS DATE))   AS [基准最早支付日],
    MAX(CAST(c.pay_date AS DATE))   AS [基准最晚支付日],
    COUNT(DISTINCT CAST(c.pay_date AS DATE)) AS [基准出现天数]
FROM missing m
INNER JOIN dbo.dwd_check_live c
    ON LTRIM(RTRIM(c.tid)) = m.tid
GROUP BY m.tid
ORDER BY m.tid;
