# -*- coding: utf-8 -*-
"""
连接器模块

管理所有外部系统的连接器
"""

from typing import Dict, Any, Optional, Type
from core.config import get_config
from core.exceptions import ConnectorNotFoundError

# 已注册的连接器
_CONNECTORS: Dict[str, Dict[str, Any]] = {}


def register_connector(name: str, info: Dict[str, Any]):
    """
    注册连接器
    
    Args:
        name: 连接器名称
        info: 连接器信息
    """
    _CONNECTORS[name] = info


def get_connector_info(name: str) -> Optional[Dict[str, Any]]:
    """获取连接器信息"""
    return _CONNECTORS.get(name)


def list_connectors() -> Dict[str, Dict[str, Any]]:
    """列出所有已注册的连接器"""
    return _CONNECTORS.copy()


def is_connector_enabled(name: str) -> bool:
    """检查连接器是否启用"""
    config = get_config()
    return config.is_connector_enabled(name)


# 自动注册连接器
def _auto_register():
    """自动发现并注册连接器"""
    # 旺店通连接器
    try:
        from .wdt import CONNECTOR_INFO as WDT_INFO
        register_connector('wdt', WDT_INFO)
    except ImportError:
        pass
    
    # 微伴助手连接器
    try:
        from .weiban import CONNECTOR_INFO as WEIBAN_INFO
        register_connector('weiban', WEIBAN_INFO)
    except ImportError:
        pass

    # 微信小店连接器
    try:
        from .wechat_store import CONNECTOR_INFO as WECHAT_STORE_INFO
        register_connector('wechat_store', WECHAT_STORE_INFO)
    except ImportError:
        pass
    
    # 其他连接器可以在这里添加...


_auto_register()

