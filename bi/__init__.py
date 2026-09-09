# -*- coding: utf-8 -*-
"""BI 报表计算任务（库内 SQL → 结果表，与 ODS/DWD 无关）"""

from .registry import get_task, list_tasks, register_task
from .runner import run_bi_task, resolve_bi_date_range

__all__ = [
    'get_task',
    'list_tasks',
    'register_task',
    'run_bi_task',
    'resolve_bi_date_range',
]
