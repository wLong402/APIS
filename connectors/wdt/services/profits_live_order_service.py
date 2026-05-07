# -*- coding: utf-8 -*-

import hashlib
import json
from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import ProfitsLiveOrderRepository
from ..sdk.api import ProfitsLiveOrderQueryAPI


class ProfitsLiveOrderPullService(BasePullService):
    SERVICE_NAME = 'profits_live_order'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'profits_live_order_query'

    def __init__(self, client: WdtClient = None, repository: ProfitsLiveOrderRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or ProfitsLiveOrderRepository()
        super().__init__(self.client, self.repo)

    @property
    def profits_live_order_api(self) -> ProfitsLiveOrderQueryAPI:
        return self.client.profits_live_order_api

    def _build_row_key(self, item: Dict) -> str:
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
        end_date = end_time.split(' ')[0] if ' ' in end_time else end_time

        call_params = dict(
            start_date=start_date,
            end_date=end_date,
            terms_income=str(kwargs.get('terms_income') or '1'),
            shop_nos=kwargs.get('shop_nos'),
            order_tools=kwargs.get('order_tools'),
            cost_type=kwargs.get('cost_type'),
        )
        print(f"[PARAMS DEBUG] profits_live_order query_all 传参: {call_params}", flush=True)

        data = self.profits_live_order_api.query_all(
            start_date=start_date,
            end_date=end_date,
            terms_income=str(kwargs.get('terms_income') or '1'),
            shop_nos=kwargs.get('shop_nos'),
            order_tools=kwargs.get('order_tools'),
            cost_type=kwargs.get('cost_type'),
            debug=kwargs.get('debug', False),
        )

        for item in data:
            item['rowKey'] = self._build_row_key(item)

        return data
