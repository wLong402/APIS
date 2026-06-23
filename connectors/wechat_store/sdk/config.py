# -*- coding: utf-8 -*-
"""微信小店 SDK 配置"""

from dataclasses import dataclass


@dataclass
class WechatStoreConfig:
    appid: str = ''
    secret: str = ''
    timeout: int = 30
    token_cache_path: str = './wechat_store_token.conf'
    stable_token_url: str = 'https://api.weixin.qq.com/cgi-bin/stable_token'
    order_get_url: str = 'https://api.weixin.qq.com/channels/ec/order/get'
