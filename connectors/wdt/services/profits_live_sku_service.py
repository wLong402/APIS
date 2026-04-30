# -*- coding: utf-8 -*-

import hashlib
import json
from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import ProfitsLiveSkuRepository
from ..sdk.api import ProfitsLiveSkuQueryAPI


class ProfitsLiveSkuPullService(BasePullService):
    SERVICE_NAME = 'profits_live_sku'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'profits_live_sku_query'

    def __init__(self, client: WdtClient = None, repository: ProfitsLiveSkuRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or ProfitsLiveSkuRepository()
        super().__init__(self.client, self.repo)

    @property
    def profits_live_sku_api(self) -> ProfitsLiveSkuQueryAPI:
        return self.client.profits_live_sku_api

    def _build_row_key(self, item: Dict) -> str:
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
        end_date = end_time.split(' ')[0] if ' ' in end_time else end_time

        call_params = dict(
            start_date=start_date,
            end_date=end_date,
            scheme_name=kwargs.get('scheme_name') or '资金账单达人方案',
            terms_income=str(kwargs.get('terms_income') or '6'),
            composite_dim=str(kwargs.get('composite_dim') or '32'),
            shop_nos=kwargs.get('shop_nos'),
            cost_type=kwargs.get('cost_type') or '0',
        )
        print(f"[PARAMS DEBUG] profits_live_sku query_all 传参: {call_params}", flush=True)

        data = self.profits_live_sku_api.query_all(
            start_date=start_date,
            end_date=end_date,
            scheme_name=kwargs.get('scheme_name') or '资金账单达人方案',
            terms_income=str(kwargs.get('terms_income') or '6'),
            composite_dim=str(kwargs.get('composite_dim') or '32'),
            shop_nos=kwargs.get('shop_nos'),
            cost_type=kwargs.get('cost_type') or '0',
            debug=kwargs.get('debug', False),
        )

        for item in data:
            item['rowKey'] = self._build_row_key(item)

        return data
