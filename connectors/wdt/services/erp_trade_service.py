# -*- coding: utf-8 -*-
"""
ERP订单拉取服务
"""

from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import ErpTradeRepository


class ErpTradePullService(BasePullService):
    """
    ERP订单拉取服务
    
    从旺店通拉取ERP订单数据并保存到数据库
    """
    
    SERVICE_NAME = 'erp_trade'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'erp_trade'
    
    def __init__(self, client: WdtClient = None, repository: ErpTradeRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or ErpTradeRepository()
        super().__init__(self.client, self.repo)
    
    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        """从 API 获取ERP订单数据"""
        return self.client.trade_query_api.query_all(
            start_time=start_time,
            end_time=end_time,
            time_type=kwargs.get('time_type', 1),
            page_size=kwargs.get('page_size', 200),
            debug=kwargs.get('debug', False),
            max_workers=kwargs.get('max_workers', 10)
        )
