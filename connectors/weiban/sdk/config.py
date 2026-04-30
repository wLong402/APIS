# -*- coding: utf-8 -*-
"""
微伴 SDK 配置
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WeibanConfig:
    """
    微伴 API 配置
    
    Attributes:
        base_url: API 基础地址
        corp_id: 企业ID
        secret: 应用密钥
        timeout: 请求超时时间（秒）
        token_cache_path: Token 缓存文件路径
    """
    base_url: str = 'https://open.weibanzhushou.com'
    corp_id: str = ''
    secret: str = ''
    timeout: int = 30
    token_cache_path: str = './access_token.conf'
    
    def __post_init__(self):
        # 确保 base_url 不以斜杠结尾
        if self.base_url.endswith('/'):
            self.base_url = self.base_url.rstrip('/')

