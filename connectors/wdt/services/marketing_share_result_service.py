# -*- coding: utf-8 -*-

import hashlib
import json
from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import MarketingShareResultRepository
from ..sdk.api import MarketingShareResultQueryAPI


class MarketingShareResultPullService(BasePullService):
    SERVICE_NAME = 'marketing_share_result'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'marketing_share_result_query'

    def __init__(self, client: WdtClient = None, repository: MarketingShareResultRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or MarketingShareResultRepository()
        super().__init__(self.client, self.repo)

    @property
    def marketing_share_result_api(self) -> MarketingShareResultQueryAPI:
        return self.client.marketing_share_result_api

    def _build_row_key(self, item: Dict) -> str:
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
        end_date = end_time.split(' ')[0] if ' ' in end_time else end_time

        data = self.marketing_share_result_api.query_all(
            event_day_start=start_date,
            event_day_end=end_date,
            shop_no=kwargs.get('shop_no'),
            spec_no=kwargs.get('spec_no'),
            project=kwargs.get('project'),
            page_size=kwargs.get('page_size', 100),
            debug=kwargs.get('debug', False),
        )

        for item in data:
            item['rowKey'] = self._build_row_key(item)

        return data
