# -*- coding: utf-8 -*-

import hashlib
import json
from typing import List, Dict, Optional

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import ReconDztkSummaryRepository
from ..sdk.api import ReconDztkSummaryQueryAPI


def _split_csv(val) -> Optional[List[str]]:
    if not val or not str(val).strip():
        return None
    return [x.strip() for x in str(val).split(',') if x.strip()]


class ReconDztkSummaryPullService(BasePullService):
    SERVICE_NAME = 'recon_dztk_summary'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'recon_dztk_summary_query'

    def __init__(self, client: WdtClient = None, repository: ReconDztkSummaryRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or ReconDztkSummaryRepository()
        super().__init__(self.client, self.repo)

    @property
    def recon_dztk_summary_api(self) -> ReconDztkSummaryQueryAPI:
        return self.client.recon_dztk_summary_api

    def _build_row_key(self, item: Dict) -> str:
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _build_query_params(self, start_time: Optional[str], end_time: Optional[str], **kwargs) -> Dict:
        start_date = None
        end_date = None
        if start_time:
            start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
        if end_time:
            end_date = end_time.split(' ')[0] if ' ' in end_time else end_time

        shop_list = None
        if kwargs.get('shop_nos'):
            shop_list = _split_csv(kwargs['shop_nos'])
        elif kwargs.get('shop_no'):
            shop_list = [str(kwargs['shop_no']).strip()]

        # 文档参数名为 refundTypes；兼容 CLI/Web 的 refund_type
        refund_types = _split_csv(kwargs.get('refund_types') or kwargs.get('refund_type'))

        return {
            'start_date': start_date,
            'end_date': end_date,
            'period_mark': kwargs.get('period_mark'),
            'shop_nos': shop_list,
            'refund_types': refund_types,
            'debug': kwargs.get('debug', False),
        }

    def _fetch_data(self, start_time: Optional[str], end_time: Optional[str], **kwargs) -> List[Dict]:
        query_params = self._build_query_params(start_time, end_time, **kwargs)
        if not query_params.get('period_mark') and not (
            query_params.get('start_date') and query_params.get('end_date')
        ):
            raise ValueError(
                'recon_dztk_summary 需传 periodMark，或同时传 startDate/endDate（二者不能都为空）'
            )

        data = self.recon_dztk_summary_api.query_all(
            period_mark=query_params.get('period_mark'),
            start_date=query_params.get('start_date'),
            end_date=query_params.get('end_date'),
            refund_types=query_params.get('refund_types'),
            shop_nos=query_params.get('shop_nos'),
            debug=query_params.get('debug', False),
        )

        for item in data:
            item['rowKey'] = self._build_row_key(item)
        return data
