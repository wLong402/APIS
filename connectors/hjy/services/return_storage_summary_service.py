# -*- coding: utf-8 -*-
"""退货入库汇总拉取：wdt.hjy.recon.return.storage.summary.query（按 businessDate 日粒度）"""

import hashlib
import json
from typing import List, Dict, Optional

from common.base_service import BasePullService
from ..client import get_hjy_client
from ..repositories import ReconReturnStorageSummaryRepository
from ..sdk.api import ReconReturnStorageSummaryQueryAPI


def _split_csv(val) -> Optional[List[str]]:
    if not val or not str(val).strip():
        return None
    return [x.strip() for x in str(val).split(',') if x.strip()]


class ReconReturnStorageSummaryPullService(BasePullService):
    SERVICE_NAME = 'recon_return_storage_summary'
    SYSTEM_NAME = 'hjy'
    API_NAME = 'recon_return_storage_summary_query'

    def __init__(self, client=None, repository: ReconReturnStorageSummaryRepository = None):
        self.client = client or get_hjy_client()
        self.repo = repository or ReconReturnStorageSummaryRepository()
        super().__init__(self.client, self.repo)

    @property
    def return_storage_summary_api(self) -> ReconReturnStorageSummaryQueryAPI:
        return self.client.recon_return_storage_summary_api

    def _build_row_key(self, item: Dict, occurrence: int = 0) -> str:
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        if occurrence:
            raw = f"{raw}#{occurrence}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        business_date = start_time.split(' ')[0] if start_time and ' ' in start_time else (start_time or '')[:10]
        if not business_date:
            raise ValueError('recon_return_storage_summary 必须提供 businessDate（可用 --start）')

        shop_list = None
        if kwargs.get('shop_nos'):
            shop_list = _split_csv(kwargs['shop_nos'])
        elif kwargs.get('shop_no'):
            shop_list = [str(kwargs['shop_no']).strip()]

        wh = kwargs.get('warehouse_nos') or kwargs.get('warehouse_no')
        data = self.return_storage_summary_api.query_all(
            business_date=business_date,
            shop_no=shop_list,
            warehouse_no=_split_csv(wh) if wh else None,
            spec_no=_split_csv(kwargs.get('spec_no')),
            summary_no=_split_csv(kwargs.get('summary_no')),
            refund_stage=kwargs.get('refund_stage') or kwargs.get('refund_type'),
            salesman_name=kwargs.get('salesman_name'),
            author_name=kwargs.get('author_name'),
            goods_batch_no=kwargs.get('goods_batch_no'),
            debug=kwargs.get('debug', False),
        )

        occurrence_counter: Dict[str, int] = {}
        for item in data:
            content_key = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
            occ = occurrence_counter.get(content_key, 0)
            occurrence_counter[content_key] = occ + 1
            item['rowKey'] = self._build_row_key(item, occurrence=occ)
        return data
