# -*- coding: utf-8 -*-
"""
自定义异常模块
"""


class DataSyncException(Exception):
    """数据同步平台基础异常"""
    
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
    
    def __str__(self):
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class ConfigError(DataSyncException):
    """配置错误"""
    pass


class DatabaseError(DataSyncException):
    """数据库错误"""
    pass


class APIError(DataSyncException):
    """API调用错误"""
    
    def __init__(self, message: str, status_code: int = None, 
                 response: dict = None, **kwargs):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response = response


class RetryExhaustedError(DataSyncException):
    """重试次数耗尽"""
    
    def __init__(self, message: str, retry_count: int = 0, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_count = retry_count


class ConnectorNotFoundError(DataSyncException):
    """连接器未找到"""
    pass


class ServiceNotFoundError(DataSyncException):
    """服务未找到"""
    pass

