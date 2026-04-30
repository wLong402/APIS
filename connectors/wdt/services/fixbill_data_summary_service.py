# -*- coding: utf-8 -*-

import hashlib
import json
from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import FixbillDataSummaryRepository
from ..sdk.api import FixbillDataSummaryQueryAPI


class FixbillDataSummaryPullService(BasePullService):
    SERVICE_NAME = 'fixbill_data_summary'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'fixbill_data_summary_query'

    def __init__(self, client: WdtClient = None, repository: FixbillDataSummaryRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or FixbillDataSummaryRepository()
        super().__init__(self.client, self.repo)

    @property
    def fixbill_data_summary_api(self) -> FixbillDataSummaryQueryAPI:
        return self.client.fixbill_data_summary_api

    def _build_row_key(self, item: Dict) -> str:
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
        end_date = end_time.split(' ')[0] if ' ' in end_time else end_time

        start_config_record_time = kwargs.get('start_config_record_time')
        end_config_record_time = kwargs.get('end_config_record_time')
        if start_config_record_time and ' ' in start_config_record_time:
            start_config_record_time = start_config_record_time.split(' ')[0]
        if end_config_record_time and ' ' in end_config_record_time:
            end_config_record_time = end_config_record_time.split(' ')[0]

        data = self.fixbill_data_summary_api.query_all(
            start_share_time=start_date,
            end_share_time=end_date,
            is_summary=str(kwargs.get('is_summary', '0')),
            classification_name=kwargs.get('classification_name'),
            start_config_record_time=start_config_record_time,
            end_config_record_time=end_config_record_time,
            shop_no=kwargs.get('shop_no'),
            page_size=kwargs.get('page_size', 100),
            debug=kwargs.get('debug', False),
        )

        for item in data:
            item['rowKey'] = self._build_row_key(item)

        return data
