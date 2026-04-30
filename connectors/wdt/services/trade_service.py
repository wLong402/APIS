# -*- coding: utf-8 -*-
"""
原始订单拉取服务
"""

from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import TradeRepository


class TradePullService(BasePullService):
    """
    原始订单拉取服务
    
    从旺店通拉取原始订单数据并保存到数据库
    """
    
    SERVICE_NAME = 'trade'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'raw_trade'
    
    def __init__(self, client: WdtClient = None, repository: TradeRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or TradeRepository()
        super().__init__(self.client, self.repo)
    
    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        """从 API 获取原始订单数据"""
        return self.client.raw_trade_api.search_all(
            start_time=start_time,
            end_time=end_time,
            time_type=kwargs.get('time_type', 3),
            shop_no=kwargs.get('shop_no'),
            page_size=kwargs.get('page_size', 200),
            debug=kwargs.get('debug', False),
            max_workers=kwargs.get('max_workers', 10)
        )
