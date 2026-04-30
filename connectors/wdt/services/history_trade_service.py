# -*- coding: utf-8 -*-
from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import HistoryTradeRepository


class HistoryTradePullService(BasePullService):
    SERVICE_NAME = 'history_trade'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'history_trade_query'
    
    def __init__(self, client: WdtClient = None, repository: HistoryTradeRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or HistoryTradeRepository()
        super().__init__(self.client, self.repo)
    
    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        return self.client.history_trade_api.query_time_range(
            start_time=start_time,
            end_time=end_time,
            shop_no=kwargs.get('shop_no'),
            time_type=kwargs.get('time_type', 1),
            page_size=kwargs.get('page_size', 200),
            debug=kwargs.get('debug', False),
            max_workers=kwargs.get('max_workers', 5)
        )




