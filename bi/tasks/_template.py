# -*- coding: utf-8 -*-
"""
BI 任务模板 — 复制此文件到 bi/tasks/ 并修改后，在 bi/tasks/__init__.py 中 import。

步骤:
  1. 定义 CREATE TABLE（结果表，建议 bi_ 前缀）
  2. 实现 build_select_sql(start_date, end_date) -> SELECT ...（列名与目标表一致）
  3. register_task(BiTask(...))
  4. 在 bi/tasks/__init__.py 增加 import
"""

from bi.registry import register_task
from bi.task import BiTask


CREATE_TABLE_SQL = """
IF OBJECT_ID(N'dbo.bi_example_daily', N'U') IS NULL
CREATE TABLE dbo.bi_example_daily (
    biz_date DATE NOT NULL PRIMARY KEY,
    metric_value DECIMAL(19, 4) NULL,
    computed_at DATETIME NOT NULL DEFAULT (GETDATE())
);
"""


def _build_select_sql(start_date: str, end_date: str) -> str:
    return f"""
SELECT
    CAST(some_date AS DATE) AS biz_date,
    SUM(some_amount) AS metric_value,
    GETDATE() AS computed_at
FROM dbo.your_source_table
WHERE CAST(some_date AS DATE) BETWEEN '{start_date}' AND '{end_date}'
GROUP BY CAST(some_date AS DATE)
"""


# register_task(BiTask(
#     name='example_daily',
#     label='示例日报',
#     description='说明此任务用途',
#     target_table='bi_example_daily',
#     date_column='biz_date',
#     create_table_sql=CREATE_TABLE_SQL,
#     build_select_sql=_build_select_sql,
# ))
