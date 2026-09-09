# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class BiTask:
    """
    BI 计算任务定义。

    新增任务：在 bi/tasks/ 下建模块，调用 register_task() 注册即可。

    两种写法二选一：
      - build_select_sql(start, end) -> SELECT（可含 CTE），由 runner 包 INSERT
      - build_batch_sql(start, end, table_ref) -> 完整批处理（临时表+索引+INSERT），同一连接执行
    """

    name: str
    label: str
    description: str
    target_table: str
    date_column: str
    create_table_sql: str
    build_select_sql: Optional[Callable[[str, str], str]] = None
    target_database: Optional[str] = None
    build_batch_sql: Optional[Callable[[str, str, str], str]] = None

    def select_sql(self, start_date: str, end_date: str) -> str:
        if not self.build_select_sql:
            raise ValueError(f'任务 {self.name} 未定义 build_select_sql')
        return self.build_select_sql(start_date, end_date)

    def batch_sql(self, start_date: str, end_date: str, table_ref: str) -> str:
        if not self.build_batch_sql:
            raise ValueError(f'任务 {self.name} 未定义 build_batch_sql')
        return self.build_batch_sql(start_date, end_date, table_ref)
