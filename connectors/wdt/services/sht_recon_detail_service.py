# -*- coding: utf-8 -*-

from typing import List, Dict, Optional

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import ShtReconDetailRepository
from ..sdk.api import ShtReconDetailQueryAPI


class ShtReconDetailPullService(BasePullService):
    SERVICE_NAME = 'sht_recon_detail'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'sht_recon_detail_query'

    def __init__(self, client: WdtClient = None, repository: ShtReconDetailRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or ShtReconDetailRepository()
        super().__init__(self.client, self.repo)

    @property
    def sht_recon_detail_api(self) -> ShtReconDetailQueryAPI:
        return self.client.sht_recon_detail_api

    def _fetch_data(self, start_time: Optional[str], end_time: Optional[str], **kwargs) -> List[Dict]:
        start_date = None
        end_date = None
        if start_time:
            start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
        if end_time:
            end_date = end_time.split(' ')[0] if ' ' in end_time else end_time

        shop_list = None
        if kwargs.get('shop_nos'):
            shop_list = [x.strip() for x in kwargs['shop_nos'].split(',') if x.strip()]
        elif kwargs.get('shop_no'):
            shop_list = [kwargs['shop_no'].strip()]

        data = self.sht_recon_detail_api.query_all(
            start_date=start_date,
            end_date=end_date,
            period_mark=kwargs.get('period_mark'),
            shop_no=shop_list,
            reco_status=kwargs.get('reco_status', '').split(',') if kwargs.get('reco_status') else None,
            refund_type=kwargs.get('refund_type', '').split(',') if kwargs.get('refund_type') else None,
            debug=kwargs.get('debug', False),
        )

        return data
