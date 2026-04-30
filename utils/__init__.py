# -*- coding: utf-8 -*-
"""
工具模块

为了向后兼容，日志函数从 core.logger 重新导出
"""

# 日志函数（从 core.logger 导入，保持向后兼容）
from core.logger import (
    get_logger, 
    get_anomaly_logger,
    log_data_mismatch, 
    log_empty_pages,
    debug_print
)

# 任务队列（可选，依赖 Redis）
try:
    from .task_queue import (
        TaskQueue, RetryTask, 
        get_task_queue, add_mismatch_task,
        create_task_queue_from_config
    )
    TASK_QUEUE_AVAILABLE = True
except ImportError:
    TASK_QUEUE_AVAILABLE = False

__all__ = [
    # 日志（从 core.logger 重新导出）
    'get_logger', 'get_anomaly_logger', 'log_data_mismatch', 'log_empty_pages', 'debug_print',
    # 任务队列
    'TaskQueue', 'RetryTask', 'get_task_queue', 'add_mismatch_task',
    'TASK_QUEUE_AVAILABLE'
]
