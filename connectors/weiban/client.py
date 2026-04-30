# -*- coding: utf-8 -*-
"""
微伴 API 客户端

封装微伴助手 API 的调用逻辑
"""

from typing import Dict, Any, Optional

from common.base_client import BaseAPIClient
from core.config import get_config

# 底层 SDK
from .sdk import WeibanAPIClient, WeibanConfig
from .sdk.api import ExternalUserAPI


class WeibanClient(BaseAPIClient):
    """
    微伴 API 客户端
    
    封装各种 API 的调用，提供统一的接口。
    
    使用方式:
        client = WeibanClient()
        users = client.external_user_api.list_all(...)
    """
    
    SYSTEM_NAME = 'weiban'
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化客户端
        
        Args:
            config: 配置字典，为空时从全局配置加载
        """
        # 加载配置
        if config is None:
            app_config = get_config()
            config = app_config.get_connector_config('weiban') or {}
        
        super().__init__(config)
        
        # 创建 WeibanConfig
        self._weiban_config = WeibanConfig(
            base_url=config.get('base_url', 'https://open.weibanzhushou.com'),
            corp_id=config.get('corp_id', ''),
            secret=config.get('secret', ''),
            timeout=config.get('timeout', 30),
            token_cache_path=config.get('token_cache_path', './access_token.conf'),
        )
        
        # 创建底层客户端
        self._api_client = WeibanAPIClient(self._weiban_config)
        
        # 初始化各 API（懒加载）
        self._external_user_api = None
    
    def call(self, method: str, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        调用 API
        
        Args:
            method: API 方法名（端点路径）
            params: 请求参数
            **kwargs: 其他参数（debug 等）
            
        Returns:
            API 响应
        """
        debug = kwargs.pop('debug', False)
        return self._api_client.get(method, params, debug=debug)
    
    @property
    def external_user_api(self) -> ExternalUserAPI:
        """客户管理 API"""
        if self._external_user_api is None:
            self._external_user_api = ExternalUserAPI(self._api_client)
        return self._external_user_api
    
    def health_check(self) -> bool:
        """健康检查 - 尝试调用 API 检查连接"""
        try:
            # 尝试获取一条数据来检查连接
            result = self.external_user_api.list(limit=1)
            return result.get('errcode') == 0
        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")
            return False


# 全局客户端实例
_weiban_client: Optional[WeibanClient] = None


def get_weiban_client() -> WeibanClient:
    """获取全局微伴客户端"""
    global _weiban_client
    if _weiban_client is None:
        _weiban_client = WeibanClient()
    return _weiban_client

