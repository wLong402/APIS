# -*- coding: utf-8 -*-
"""
统一日志模块

提供结构化日志记录能力
"""

import os
import sys
import logging
import shutil
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

try:
    from concurrent_log_handler import ConcurrentRotatingFileHandler
    _HAS_CONCURRENT_HANDLER = True
except ImportError:
    _HAS_CONCURRENT_HANDLER = False

# 确保日志目录存在
LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 日志格式
LOG_FORMAT = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 日志记录器缓存
_loggers = {}


class WindowsSafeRotatingFileHandler(RotatingFileHandler):
    """
    Windows 兼容的日志轮转处理器
    
    解决 Windows 上文件被占用时无法重命名的问题
    使用复制+截断的方式代替重命名
    """
    
    def doRollover(self):
        """
        执行日志轮转
        
        在 Windows 上如果重命名失败，使用复制+截断的方式
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename("%s.%d" % (self.baseFilename, i))
                dfn = self.rotation_filename("%s.%d" % (self.baseFilename, i + 1))
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    # 尝试重命名，失败则使用复制
                    try:
                        os.rename(sfn, dfn)
                    except (OSError, IOError):
                        # Windows 上文件被占用时，使用复制+删除
                        if os.path.exists(dfn):
                            os.remove(dfn)
                        shutil.copy2(sfn, dfn)
                        try:
                            os.remove(sfn)
                        except (OSError, IOError):
                            # 如果删除失败，忽略（文件可能被占用）
                            pass
            
            dfn = self.rotation_filename(self.baseFilename + ".1")
            if os.path.exists(self.baseFilename):
                # 尝试重命名，失败则使用复制+截断
                try:
                    os.rename(self.baseFilename, dfn)
                except (OSError, IOError):
                    # Windows 上文件被占用时，使用复制+截断
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    shutil.copy2(self.baseFilename, dfn)
                    # 截断原文件
                    try:
                        with open(self.baseFilename, 'w', encoding=self.encoding):
                            pass
                    except (OSError, IOError):
                        # 如果截断失败，忽略（文件可能被占用）
                        pass
        
        if not self.delay:
            self.stream = self._open()


def get_logger(name: str = 'app', log_file: str = None) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称，支持点号分隔的层级名称
              如 'connector.wdt.trade'
        log_file: 日志文件名（默认为 {name}.log 或 app.log）
    
    Returns:
        logging.Logger
    """
    # 使用缓存避免重复创建
    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    
    # 避免重复添加 handler
    if logger.handlers:
        _loggers[name] = logger
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # 确定日志文件名
    if log_file is None:
        # 使用顶级名称作为文件名
        top_name = name.split('.')[0]
        if top_name in ('connector', 'service', 'repository', 'api', 'scheduler'):
            log_file = 'app.log'
        else:
            log_file = f'{top_name}.log'
    
    if _HAS_CONCURRENT_HANDLER:
        file_handler = ConcurrentRotatingFileHandler(
            os.path.join(LOG_DIR, log_file),
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8',
            use_gzip=True,
        )
    elif sys.platform == 'win32':
        file_handler = WindowsSafeRotatingFileHandler(
            os.path.join(LOG_DIR, log_file),
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
    else:
        file_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, log_file),
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(file_handler)
    
    # 控制台 handler（可选，仅在开发环境）
    if os.getenv('ENV', 'development') == 'development':
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        # logger.addHandler(console_handler)  # 暂不添加，避免重复输出
    
    _loggers[name] = logger
    return logger


# ============ 异常日志（专用） ============

_anomaly_logger: Optional[logging.Logger] = None


def get_anomaly_logger() -> logging.Logger:
    """获取数据异常日志记录器"""
    global _anomaly_logger
    if _anomaly_logger is None:
        _anomaly_logger = get_logger('data_anomaly', 'data_anomaly.log')
    return _anomaly_logger


def log_data_mismatch(api_name: str, time_range: str, expected: int, actual: int, 
                      empty_pages: list = None, failed_pages: list = None,
                      connector: str = None):
    """
    记录数据总数不匹配异常
    
    Args:
        api_name: API名称（如 raw_trade, raw_refund, erp_trade）
        time_range: 时间范围
        expected: API返回的总数
        actual: 实际获取的数据条数
        empty_pages: 空页列表
        failed_pages: 失败页列表
        connector: 连接器名称（如 wdt）
    """
    logger = get_anomaly_logger()
    
    diff = expected - actual
    diff_percent = (diff / expected * 100) if expected > 0 else 0
    
    prefix = f"[{connector}]" if connector else ""
    
    msg_parts = [
        f"{prefix}[数据不匹配] {api_name}",
        f"时间范围: {time_range}",
        f"预期: {expected}",
        f"实际: {actual}",
        f"差异: {diff} ({diff_percent:.2f}%)"
    ]
    
    if empty_pages:
        msg_parts.append(f"空页({len(empty_pages)}): {sorted(empty_pages)[:20]}{'...' if len(empty_pages) > 20 else ''}")
    
    if failed_pages:
        msg_parts.append(f"失败页({len(failed_pages)}): {failed_pages[:10]}{'...' if len(failed_pages) > 10 else ''}")
    
    logger.warning(' | '.join(msg_parts))


def log_empty_pages(api_name: str, time_range: str, empty_pages: list, 
                    retry_recovered: int = 0, still_empty: list = None,
                    connector: str = None):
    """
    记录空页异常
    
    Args:
        api_name: API名称
        time_range: 时间范围
        empty_pages: 初始空页列表
        retry_recovered: 重试后恢复的页数
        still_empty: 重试后仍为空的页列表
        connector: 连接器名称
    """
    logger = get_anomaly_logger()
    
    if still_empty is None:
        still_empty = []
    
    prefix = f"[{connector}]" if connector else ""
    
    msg_parts = [
        f"{prefix}[空页异常] {api_name}",
        f"时间范围: {time_range}",
        f"初始空页: {len(empty_pages)}",
        f"重试恢复: {retry_recovered}",
        f"最终空页: {len(still_empty)}"
    ]
    
    if still_empty:
        msg_parts.append(f"空页列表: {sorted(still_empty)[:30]}{'...' if len(still_empty) > 30 else ''}")
    
    if still_empty:
        logger.warning(' | '.join(msg_parts))
    else:
        logger.info(' | '.join(msg_parts))


# ============ 调试打印（带时间戳） ============

def debug_print(msg: str, end: str = '\n', flush: bool = False):
    """
    带时间戳的 DEBUG 打印函数
    
    Args:
        msg: 要打印的消息
        end: 行结尾符
        flush: 是否立即刷新
    
    注意：如果消息以 \\r 开头（进度条覆盖模式），则不添加时间戳
    """
    # 进度条模式：以 \r 开头时不加时间戳，保证回车覆盖正常工作
    if msg.startswith('\r'):
        print(msg, end=end, flush=flush)
    else:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} | {msg}", end=end, flush=flush)

