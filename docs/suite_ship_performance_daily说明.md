# suite_ship_performance_daily 说明

> 套组发货业绩（按日）— 库内 BI 计算任务  
> 代码：`bi/tasks/suite_ship_performance_daily.py`  
> 调度：定时任务「套组」，每天 01:00（见 `web/data/schedules.json`）

---

## 一、基本信息

| 项 | 内容 |
|----|------|
| 任务名 | `suite_ship_performance_daily` |
| 中文名 | 套组发货业绩（按日） |
| 类型 | **库内计算**，无外部 HTTP 接口 |
| 入口 | Web「数据库任务」/ CLI `bi` / 定时调度 `bi_task` |
| 框架 | `bi/runner.py` 调 `build_batch_sql`，同连接按 `GO` 分批执行 |
| 运行模式 | `auto`（目标表空→全量；有数据→窗口增量）/ `window` / `full` |

**不是 API 拉取任务**：不调奇门 / 慧经营；只读 dwd + BI 维表，写入 BI 结果表。

---

## 二、表关系

### 2.1 结果表（写入）

| 库.表 | 说明 |
|--------|------|
| `BI_lqx.dbo.bi_suite_ship_performance_daily` | 按日汇总结果 |

主键：`(biz_date, suite_no, shop_code)`

| 字段 | 含义 |
|------|------|
| `biz_date` | 业务日 |
| `suite_no` | 套组编码 |
| `shop_code` | 店铺（来自 `shop_no`，空串视为 `''`） |
| `suite_name` | 套组名称（维表） |
| `is_dabo` | 是否达播：`是` / `否` |
| `ship_order_cnt` | 发货订单数（按 stockout_id 计） |
| `ship_suite_qty` | 发货套组数量 |
| `ship_amount` | 发货金额 |
| `refund_amount` | 退货金额（已映射到套组） |
| `net_amount` | 净业绩 = `ship_amount - refund_amount` |
| `computed_at` | 计算时间 |

### 2.2 源表（只读）

| 角色 | 库.表 | 用途 |
|------|--------|------|
| 发货主 | `dwd.dbo.dwd_wdt_stockout_sales` | `consign_time`、`shop_no`、`stockout_id` |
| 发货明细 | `dwd.dbo.dwd_wdt_stockout_sales_detail` | `suite_no`、`suite_num`、`share_amount`、`goods_type`；退货反查套组也用 |
| 发货宽表（兜底） | `dwd.dbo.dwd_wdt_stockout_sales_wide` | 退货映射套组二次匹配 |
| 退货主 | `dwd.dbo.dwd_wdt_stockin_refund` | `created_time`、`shop_no` |
| 退货明细 | `dwd.dbo.dwd_wdt_stockin_refund_detail` | `spec_no`、`tid`、`actual_refund_amount` |
| 套组维表 | `BI_lqx.dbo.DIM_Goods_wdt` | `suite_no` → `suite_name`（**必须命中维表才入库**） |
| 达人维表 | `BI_lqx.dbo.MR_daren` | `sn` 判断达播 |

依赖上游：出库 / 入库 DWD 需已由拉取+清洗任务产出（注意：拉取 ODS 表名带 `_tamp2` 等，本任务读的是 **`dwd_wdt_*` DWD 表**）。

---

## 三、处理逻辑

### 3.1 总流程

```text
解析日期窗口 [start, end]
        │
        ▼
建表 / 迁移结果表结构（含 shop_code、is_dabo）
        │
        ▼
#ship_order → #ship_daily          （发货按日+套组+店汇总）
        │
#refund_src → #refund_key
        │
#suite_map（tid+spec_no → suite_no，先 detail 后 wide）
        │
#refund_line → #refund_daily       （退货映射到套组后汇总）
        │
#suite_dim / #daren_sn             （维表）
        │
#keys = 发货 ∪ 退货 键
        │
INNER JOIN 维表 + LEFT JOIN 发货/退货
        │
INSERT 结果表（窗口模式会先删窗口内旧数据）
```

粒度：**同一天 + 同一套组 + 不同店铺 = 多行**。

### 3.2 发货汇总

1. 出库主表 × 明细，时间：`consign_time ∈ [start, end+1日)`  
2. 过滤：`suite_no` 非空；`goods_type IN (0, 1)`  
3. 按 `(biz_date, suite_no, shop_code, stockout_id)` 聚合：
   - `suite_qty` = `MAX(suite_num)`
   - `suite_amount` = `SUM(share_amount)`
4. 再汇总到日维度：订单数 / 数量 / 金额 → `#ship_daily`

### 3.3 退货汇总（关键：要先反查套组）

退货明细只有 `tid` + `spec_no`，没有 `suite_no`，所以：

1. 退货主×明细，时间：`created_time ∈ [start, end+1日)`  
2. 要求 `spec_no`、`tid` 非空；金额取 `MAX(actual_refund_amount)`（按 stockin 行）  
3. 用 `(tid, spec_no)` 去出库明细找套组：
   - 优先：`dwd_wdt_stockout_sales_detail`（`src_tid` + `spec_no`，`goods_type IN (0,1)`）
   - 补漏：`dwd_wdt_stockout_sales_wide`（尚未映射到的键）
4. 映射成功后按 `(biz_date, suite_no, shop_code)` 汇总 `refund_amount`

**映不到套组的退货不会进结果。**

### 3.4 达播判定 `is_dabo`

满足任一即为「是」：

- `LEFT(suite_no, 6)` 命中 `MR_daren.sn`
- 或 `suite_no` 以 `DB0000` 开头

### 3.5 净业绩

```text
net_amount = ISNULL(ship_amount, 0) - ISNULL(refund_amount, 0)
```

只有发货或只有退货的键也会出现（另一侧为 0），但 **必须在 `DIM_Goods_wdt` 有该 suite_no**（`INNER JOIN #suite_dim`），否则整行丢弃。

### 3.6 写入策略（runner）

| mode | 行为 |
|------|------|
| `full` | 清空结果表后全量（或按给定窗口重算，视 runner 实现） |
| `window` / `auto`（表已有数据） | 先删目标表中窗口内 `biz_date`，再 INSERT |
| `auto`（表为空） | 按窗口全量写入 |

实现：`bi/runner.py` + 本任务 `build_batch_sql(start, end, table_ref)`。

---

## 四、与拉取任务的关系

```text
stockout 拉取 → wdt_stockout_sales(+detail)
                      │（若另有 DWD 清洗链路）
                      ▼
              dwd_wdt_stockout_sales(+detail[/wide])
                      │
stockin 拉取  → … → dwd_wdt_stockin_refund(+detail)
                      │
                      ▼
         suite_ship_performance_daily（本任务）
                      │
                      ▼
         BI_lqx.bi_suite_ship_performance_daily
```

本仓库出库/入库拉取写的是 ODS（如 `wdt_stockout_sales`、`wdt_stockin_refund_tamp2`）；本 BI 任务读的是 **`dwd_wdt_*`**。若 DWD 未同步更新，本任务结果会偏旧或为空。

