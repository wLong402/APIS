# -*- coding: utf-8 -*-
"""
API 客户端基类

所有外部系统的 API 客户端都应继承此基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.logger import get_logger


class BaseAPIClient(ABC):
    """
    API 客户端基类
    
    所有外部系统的客户端都应继承此类，实现统一的接口规范。
    
    子类必须定义:
        - SYSTEM_NAME: 系统标识（如 'wdt', 'jdy'）
        
    子类必须实现:
        - call(): API 调用方法
    """
    
    # 系统标识（子类必须定义）
    SYSTEM_NAME: str = None
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化客户端
        
        Args:
            config: 客户端配置字典
        """
        if self.SYSTEM_NAME is None:
            raise NotImplementedError("子类必须定义 SYSTEM_NAME")
        
        self.config = config or {}
        self.logger = get_logger(f"connector.{self.SYSTEM_NAME}.client")
    
    @abstractmethod
    def call(self, method: str, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        调用 API
        
        Args:
            method: API 方法名
            params: 请求参数
            **kwargs: 其他参数
            
        Returns:
            API 响应结果
        """
        pass
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            True 表示连接正常
        """
        return True
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(system={self.SYSTEM_NAME})>"

