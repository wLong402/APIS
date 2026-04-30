# -*- coding: utf-8 -*-

import hashlib
import json
from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import ProfitsOrderRepository
from ..sdk.api import ProfitsOrderQueryAPI


class ProfitsOrderPullService(BasePullService):
    SERVICE_NAME = 'profits_order'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'profits_order_query'

    def __init__(self, client: WdtClient = None, repository: ProfitsOrderRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or ProfitsOrderRepository()
        super().__init__(self.client, self.repo)

    @property
    def profits_order_api(self) -> ProfitsOrderQueryAPI:
        return self.client.profits_order_api

    def _build_row_key(self, item: Dict) -> str:
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
        end_date = end_time.split(' ')[0] if ' ' in end_time else end_time

        call_params = dict(
            start_date=start_date,
            end_date=end_date,
            scheme_name=kwargs.get('scheme_name', '系统方案'),
            terms_income=str(kwargs.get('terms_income', '1')),
            split_suite=str(kwargs.get('split_suite', '0')),
            original_order=str(kwargs.get('original_order', '0')),
            shop_nos=kwargs.get('shop_nos'),
            plat_order_nos=kwargs.get('plat_order_nos'),
            erp_order_nos=kwargs.get('erp_order_nos'),
            order_way=kwargs.get('order_way'),
            cost_type=kwargs.get('cost_type') or '0',
            stat_mode=kwargs.get('stat_mode') or '1',
            composite_dim=kwargs.get('composite_dim') or '7',
        )
        print(f"[PARAMS DEBUG] profits_order query_all 传参: {call_params}", flush=True)

        data = self.profits_order_api.query_all(
            start_date=start_date,
            end_date=end_date,
            scheme_name=kwargs.get('scheme_name', '系统方案'),
            terms_income=str(kwargs.get('terms_income', '1')),
            split_suite=str(kwargs.get('split_suite', '0')),
            original_order=str(kwargs.get('original_order', '0')),
            shop_nos=kwargs.get('shop_nos'),
            plat_order_nos=kwargs.get('plat_order_nos'),
            erp_order_nos=kwargs.get('erp_order_nos'),
            order_way=kwargs.get('order_way'),
            cost_type=kwargs.get('cost_type') or '0',
            stat_mode=kwargs.get('stat_mode') or '1',
            composite_dim=kwargs.get('composite_dim') or '7',
            debug=kwargs.get('debug', False),
        )

        for item in data:
            item['rowKey'] = self._build_row_key(item)

        return data
