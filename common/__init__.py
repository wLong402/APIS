# -*- coding: utf-8 -*-
"""
通用模块

提供基类和通用工具
"""

from .base_client import BaseAPIClient
from .base_service import BasePullService, PullResult
from .base_repository import BaseRepository
from .retry import (
    RetryPolicy,
    BackoffStrategy,
    ConstantBackoff,
    LinearBackoff,
    ExponentialBackoff,
    retry,
    retry_call,
    API_RETRY_POLICY,
    DB_RETRY_POLICY,
    QUEUE_RETRY_POLICY,
)

__all__ = [
    # 基类
    'BaseAPIClient',
    'BasePullService',
    'PullResult',
    'BaseRepository',
    # 重试
    'RetryPolicy',
    'BackoffStrategy',
    'ConstantBackoff',
    'LinearBackoff', 
    'ExponentialBackoff',
    'retry',
    'retry_call',
    'API_RETRY_POLICY',
    'DB_RETRY_POLICY',
    'QUEUE_RETRY_POLICY',
]
