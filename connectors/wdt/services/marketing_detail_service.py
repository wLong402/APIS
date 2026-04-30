# -*- coding: utf-8 -*-
from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import MarketingDetailRepository
from ..sdk.api import MarketingDetailQueryAPI


class MarketingDetailPullService(BasePullService):
    SERVICE_NAME = 'marketing_detail'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'marketing_detail_query'
    
    def __init__(self, client: WdtClient = None, repository: MarketingDetailRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or MarketingDetailRepository()
        super().__init__(self.client, self.repo)
        
    @property
    def marketing_api(self) -> MarketingDetailQueryAPI:
        return self.client.marketing_detail_api
    
    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
        end_date = end_time.split(' ')[0] if ' ' in end_time else end_time
        
        shop_no = kwargs.get('shop_no')
        if isinstance(shop_no, str):
            shop_no = [shop_no]
        
        if start_date == end_date:
            return self.marketing_api.query_all(
                business_time=start_date,
                shop_no=shop_no,
                debug=kwargs.get('debug', False)
            )
        
        return self.marketing_api.query_date_range(
            start_date=start_date,
            end_date=end_date,
            shop_no=shop_no,
            debug=kwargs.get('debug', False),
            max_workers=kwargs.get('max_workers', 5)
        )




