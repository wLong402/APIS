# -*- coding: utf-8 -*-

import hashlib
import json
from typing import List, Dict, Optional

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import ReconOrderConfirmSummaryRepository
from ..sdk.api import ReconOrderConfirmSummaryQueryAPI


def _split_csv(val) -> Optional[List[str]]:
    if not val or not str(val).strip():
        return None
    return [x.strip() for x in str(val).split(',') if x.strip()]


class ReconOrderConfirmSummaryPullService(BasePullService):
    SERVICE_NAME = 'recon_order_confirm_summary'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'recon_order_confirm_summary_query'

    def __init__(self, client: WdtClient = None, repository: ReconOrderConfirmSummaryRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or ReconOrderConfirmSummaryRepository()
        super().__init__(self.client, self.repo)

    @property
    def recon_order_confirm_summary_api(self) -> ReconOrderConfirmSummaryQueryAPI:
        return self.client.recon_order_confirm_summary_api

    def _build_row_key(self, item: Dict) -> str:
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _build_query_params(self, start_time: str, end_time: str, **kwargs) -> Dict:
        start_date = start_time.split(' ')[0] if start_time and ' ' in start_time else start_time
        end_date = end_time.split(' ')[0] if end_time and ' ' in end_time else end_time

        shop_list = None
        if kwargs.get('shop_nos'):
            shop_list = _split_csv(kwargs['shop_nos'])
        elif kwargs.get('shop_no'):
            shop_list = [str(kwargs['shop_no']).strip()]

        return {
            'start_date': start_date,
            'end_date': end_date,
            'shop_no': shop_list,
            'shop_name': _split_csv(kwargs.get('shop_name')),
            'spec_no': _split_csv(kwargs.get('spec_no')),
            'summary_no': _split_csv(kwargs.get('summary_no')),
            'debug': kwargs.get('debug', False),
        }

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        query_params = self._build_query_params(start_time, end_time, **kwargs)
        if not query_params.get('start_date') or not query_params.get('end_date'):
            raise ValueError('recon_order_confirm_summary 必须传账期开始/结束日期 startDate/endDate')

        data = self.recon_order_confirm_summary_api.query_all(
            start_date=query_params['start_date'],
            end_date=query_params['end_date'],
            shop_no=query_params.get('shop_no'),
            shop_name=query_params.get('shop_name'),
            spec_no=query_params.get('spec_no'),
            summary_no=query_params.get('summary_no'),
            debug=query_params.get('debug', False),
        )

        for item in data:
            item['rowKey'] = self._build_row_key(item)
        return data
