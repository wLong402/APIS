# -*- coding: utf-8 -*-
"""
日志模块 - 兼容层

此模块已迁移到 core.logger，这里只是重新导出以保持向后兼容。
新代码请直接使用 from core.logger import ...
"""

# 从 core.logger 重新导出所有内容
from core.logger import (
    get_logger,
    get_anomaly_logger,
    log_data_mismatch,
    log_empty_pages,
    debug_print,
    LOG_DIR,
    LOG_FORMAT,
    DATE_FORMAT,
)

__all__ = [
    'get_logger',
    'get_anomaly_logger', 
    'log_data_mismatch',
    'log_empty_pages',
    'debug_print',
    'LOG_DIR',
    'LOG_FORMAT',
    'DATE_FORMAT',
]
