# -*- coding: utf-8 -*-

from typing import List, Dict

from core.logger import debug_print
from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import LogisticsTraceRepository
from ..sdk.api import SearchLogisticsTraceAPI


class LogisticsTracePullService(BasePullService):

    SERVICE_NAME = 'logistics_trace'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'search_logistics_trace'
    TIME_SPAN_MINUTES = 1440

    def __init__(self, client: WdtClient = None, repository: LogisticsTraceRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or LogisticsTraceRepository()
        super().__init__(self.client, self.repo)

    @property
    def logistics_trace_api(self) -> SearchLogisticsTraceAPI:
        return self.client.logistics_trace_api

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        debug = kwargs.get('debug', False)
        page_size = kwargs.get('page_size', 200)
        need_detail = bool(kwargs.get('need_detail'))
        logistics_no = kwargs.get('logistics_no')
        if need_detail and page_size > 100:
            page_size = 100

        logistics_status = kwargs.get('logistics_status')
        if logistics_status is not None and logistics_status != '':
            logistics_status = int(logistics_status)

        if debug:
            debug_print(f"    [DEBUG] 调用 API: {self.logistics_trace_api.METHOD}")

        return self.logistics_trace_api.search_all(
            start_time=start_time if not logistics_no else None,
            end_time=end_time if not logistics_no else None,
            logistics_status=logistics_status,
            warehouse_no=kwargs.get('warehouse_no'),
            shop_no=kwargs.get('shop_no'),
            need_detail=need_detail,
            logistics_no=logistics_no,
            page_size=page_size,
            debug=debug,
        )
