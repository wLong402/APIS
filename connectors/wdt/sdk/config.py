#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
统一管理旺店通奇门接口配置
"""

import os
import yaml
from dataclasses import dataclass
from typing import Optional


@dataclass
class WdtConfig:
    """旺店通配置类"""
    
    # 旺店通应用配置
    app_key: str
    app_secret: str
    
    # 奇门配置
    qimen_appkey: str
    qimen_appsecret: str
    gateway_url: str
    target_appkey: str
    
    # 客户标识
    wdt3_customer_id: str
    
    # 请求超时
    timeout: int = 30
    
    @property
    def wdt_secret(self) -> str:
        """获取旺店通密钥（secret部分）"""
        parts = self.app_secret.split(':')
        return parts[0]
    
    @property
    def wdt_salt(self) -> str:
        """获取旺店通盐值（salt部分）"""
        parts = self.app_secret.split(':')
        return parts[1] if len(parts) > 1 else ''
    
    @classmethod
    def from_yaml(cls, config_path: str = 'config/config.yaml') -> 'WdtConfig':
        """
        从YAML配置文件加载配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            WdtConfig实例
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        wdt_config = config.get('wdt', {})
        
        return cls(
            app_key=wdt_config.get('app_key', ''),
            app_secret=wdt_config.get('app_secret', ''),
            qimen_appkey=wdt_config.get('qimen_appkey', ''),
            qimen_appsecret=wdt_config.get('qimen_appsecret', ''),
            gateway_url=wdt_config.get('gateway_url', ''),
            target_appkey=wdt_config.get('target_appkey', ''),
            wdt3_customer_id=wdt_config.get('wdt3_customer_id', ''),
            timeout=wdt_config.get('timeout', 30)
        )
    
    @classmethod
    def from_env(cls) -> 'WdtConfig':
        """
        从环境变量加载配置
        
        Returns:
            WdtConfig实例
        """
        return cls(
            app_key=os.getenv('WDT_APP_KEY', ''),
            app_secret=os.getenv('WDT_APP_SECRET', ''),
            qimen_appkey=os.getenv('WDT_QIMEN_APPKEY', ''),
            qimen_appsecret=os.getenv('WDT_QIMEN_APPSECRET', ''),
            gateway_url=os.getenv('WDT_GATEWAY_URL', ''),
            target_appkey=os.getenv('WDT_TARGET_APPKEY', ''),
            wdt3_customer_id=os.getenv('WDT_CUSTOMER_ID', ''),
            timeout=int(os.getenv('WDT_TIMEOUT', '30'))
        )
    
    @classmethod
    def default(cls) -> 'WdtConfig':
        """
        返回默认配置（硬编码）
        
        Returns:
            WdtConfig实例
        """
        return cls(
            app_key='33457302',
            app_secret='168b0a063de6a1791c1107d9794c1511:152112177237114209c96f4a83c35fec',
            qimen_appkey='33457302',
            qimen_appsecret='6d9fe9dca09b24046dce5d27966ba28d',
            gateway_url='http://3ldsmu02o9.api.taobao.com/router/qm',
            target_appkey='21363512',
            wdt3_customer_id='lqx3',
            timeout=30
        )

