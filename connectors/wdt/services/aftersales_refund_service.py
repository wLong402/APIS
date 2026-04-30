# -*- coding: utf-8 -*-

from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import AftersalesRefundRepository


class AftersalesRefundPullService(BasePullService):
    
    SERVICE_NAME = 'aftersales_refund'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'aftersales_refund'
    
    def __init__(self, client: WdtClient = None, repository: AftersalesRefundRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or AftersalesRefundRepository()
        super().__init__(self.client, self.repo)
    
    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        shop_no = kwargs.get('shop_no') or kwargs.get('shop_nos')
        return self.client.aftersales_refund_api.search_all(
            start_time=start_time,
            end_time=end_time,
            time_type=kwargs.get('time_type', 1),
            shop_no=shop_no,
            status=kwargs.get('status'),
            page_size=kwargs.get('page_size', 200),
            debug=kwargs.get('debug', False),
            max_workers=kwargs.get('max_workers', 10)
        )
