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


def find_service_connector(service_name: str) -> Optional[str]:
    """按服务名反查它注册在哪个连接器下，找不到返回 None"""
    if not service_name:
        return None
    for name, info in _CONNECTORS.items():
        if service_name in (info.get('services') or {}):
            return name
    return None


def resolve_connector(connector: str, service_name: str) -> str:
    """
    校正连接器名。

    服务在连接器之间迁移后（如 wdt.hjy.* 从 wdt 挪到 hjy），历史命令行、
    已保存的定时任务和重跑记录里仍带着旧的连接器名。这里以“服务实际注册在哪”
    为准，避免报“未知的服务”。给定连接器本身能提供该服务时按原样返回。
    """
    info = _CONNECTORS.get(connector)
    if info and service_name in (info.get('services') or {}):
        return connector
    return find_service_connector(service_name) or connector


# 自动注册连接器
def _auto_register():
    """自动发现并注册连接器"""
    def _try_register(name: str, import_path: str, attr: str = 'CONNECTOR_INFO'):
        try:
            mod = __import__(import_path, fromlist=[attr])
            register_connector(name, getattr(mod, attr))
        except Exception as e:
            # 静默会让前端缺选项且难排查；至少打到 stderr
            import sys
            print(f"[connectors] 注册 {name} 失败: {type(e).__name__}: {e}", file=sys.stderr)

    _try_register('wdt', 'connectors.wdt')
    _try_register('weiban', 'connectors.weiban')
    _try_register('wechat_store', 'connectors.wechat_store')
    _try_register('hjy', 'connectors.hjy')


_auto_register()

