# -*- coding: utf-8 -*-
"""
重试策略模块

提供灵活的重试机制，支持多种退避策略
"""

import time
import random
from abc import ABC, abstractmethod
from typing import TypeVar, Callable, Optional, Any, List, Type
from dataclasses import dataclass, field
from functools import wraps

from core.logger import get_logger

logger = get_logger('common.retry')

T = TypeVar('T')


# ============ 退避策略 ============

class BackoffStrategy(ABC):
    """退避策略基类"""
    
    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """
        获取第 n 次重试的等待时间
        
        Args:
            attempt: 重试次数（从1开始）
            
        Returns:
            等待秒数
        """
        pass


class ConstantBackoff(BackoffStrategy):
    """固定间隔退避"""
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
    
    def get_delay(self, attempt: int) -> float:
        return self.delay


class LinearBackoff(BackoffStrategy):
    """线性增长退避"""
    
    def __init__(self, initial: float = 1.0, increment: float = 1.0, max_delay: float = 60.0):
        self.initial = initial
        self.increment = increment
        self.max_delay = max_delay
    
    def get_delay(self, attempt: int) -> float:
        delay = self.initial + (attempt - 1) * self.increment
        return min(delay, self.max_delay)


class ExponentialBackoff(BackoffStrategy):
    """指数退避（推荐用于 API 调用）"""
    
    def __init__(self, 
                 initial: float = 1.0, 
                 multiplier: float = 2.0, 
                 max_delay: float = 60.0,
                 jitter: bool = True):
        """
        Args:
            initial: 初始等待时间
            multiplier: 倍数
            max_delay: 最大等待时间
            jitter: 是否添加随机抖动（防止惊群效应）
        """
        self.initial = initial
        self.multiplier = multiplier
        self.max_delay = max_delay
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        delay = self.initial * (self.multiplier ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # 添加 ±25% 的随机抖动
            jitter_range = delay * 0.25
            delay = delay + random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)


# ============ 重试策略 ============

@dataclass
class RetryPolicy:
    """
    重试策略
    
    使用示例:
        # 简单使用
        policy = RetryPolicy(max_retries=3)
        result = policy.execute(some_function, arg1, arg2)
        
        # 指数退避
        policy = RetryPolicy(
            max_retries=5,
            backoff=ExponentialBackoff(initial=0.5, multiplier=2)
        )
        
        # 只重试特定异常
        policy = RetryPolicy(
            max_retries=3,
            retry_on=[ConnectionError, TimeoutError]
        )
    """
    
    max_retries: int = 3
    backoff: BackoffStrategy = field(default_factory=lambda: ExponentialBackoff())
    retry_on: List[Type[Exception]] = field(default_factory=lambda: [Exception])
    on_retry: Optional[Callable[[int, Exception], None]] = None  # 重试回调
    
    def should_retry(self, exception: Exception) -> bool:
        """判断是否应该重试此异常"""
        return any(isinstance(exception, exc_type) for exc_type in self.retry_on)
    
    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        执行带重试的函数调用
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数返回值
            
        Raises:
            最后一次失败的异常
        """
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if not self.should_retry(e):
                    raise
                
                if attempt < self.max_retries:
                    delay = self.backoff.get_delay(attempt)
                    
                    # 调用重试回调
                    if self.on_retry:
                        self.on_retry(attempt, e)
                    else:
                        logger.warning(f"第 {attempt} 次重试失败: {e}，{delay:.2f}秒后重试")
                    
                    time.sleep(delay)
                else:
                    logger.error(f"重试 {self.max_retries} 次后仍失败: {e}")
        
        raise last_exception


# ============ 装饰器 ============

def retry(max_retries: int = 3,
          backoff: BackoffStrategy = None,
          retry_on: List[Type[Exception]] = None,
          on_retry: Callable[[int, Exception], None] = None):
    """
    重试装饰器
    
    使用示例:
        @retry(max_retries=3)
        def fetch_data():
            ...
        
        @retry(max_retries=5, backoff=ExponentialBackoff())
        def call_api():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        policy = RetryPolicy(
            max_retries=max_retries,
            backoff=backoff or ExponentialBackoff(),
            retry_on=retry_on or [Exception],
            on_retry=on_retry
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return policy.execute(func, *args, **kwargs)
        
        return wrapper
    return decorator


# ============ 便捷函数 ============

def retry_call(func: Callable[..., T],
               args: tuple = (),
               kwargs: dict = None,
               max_retries: int = 3,
               backoff: BackoffStrategy = None) -> T:
    """
    便捷的重试调用函数
    
    Args:
        func: 要调用的函数
        args: 位置参数
        kwargs: 关键字参数
        max_retries: 最大重试次数
        backoff: 退避策略
        
    Returns:
        函数返回值
    """
    kwargs = kwargs or {}
    policy = RetryPolicy(
        max_retries=max_retries,
        backoff=backoff or ExponentialBackoff()
    )
    return policy.execute(func, *args, **kwargs)


# ============ 预定义策略 ============

# API 调用推荐策略（指数退避 + 抖动）
API_RETRY_POLICY = RetryPolicy(
    max_retries=3,
    backoff=ExponentialBackoff(initial=1.0, multiplier=2.0, max_delay=30.0, jitter=True),
    retry_on=[ConnectionError, TimeoutError, OSError]
)

# 数据库操作推荐策略（快速重试）
DB_RETRY_POLICY = RetryPolicy(
    max_retries=3,
    backoff=ConstantBackoff(delay=0.5),
)

# 任务队列推荐策略（较长退避）
QUEUE_RETRY_POLICY = RetryPolicy(
    max_retries=5,
    backoff=ExponentialBackoff(initial=5.0, multiplier=2.0, max_delay=300.0),
)

