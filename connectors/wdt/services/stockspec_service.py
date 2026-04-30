# -*- coding: utf-8 -*-

from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import StockSpecRepository


class StockSpecPullService(BasePullService):
    
    SERVICE_NAME = 'stockspec'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'stockspec'
    
    def __init__(self, client: WdtClient = None, repository: StockSpecRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or StockSpecRepository()
        super().__init__(self.client, self.repo)
    
    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        return self.client.stockspec_api.search_all(
            start_time=start_time,
            end_time=end_time,
            warehouse_no=kwargs.get('warehouse_no'),
            goods_no=kwargs.get('goods_no'),
            page_size=kwargs.get('page_size', 200),
            debug=kwargs.get('debug', False),
            max_workers=kwargs.get('max_workers', 10)
        )

