# -*- coding: utf-8 -*-
"""退货入库单拉取（旗舰 OpenAPI wms.stockin.Refund.queryWithDetail）"""

from typing import List, Dict, Optional

from core.logger import debug_print
from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories.openapi_stockin_refund_repo import OpenapiStockinRefundRepository
from ..sdk.api.stockin_refund_openapi import QueryStockinRefundOpenAPI


def _as_bool(val) -> Optional[bool]:
    if val is None or val == '':
        return None
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ('1', 'true', 'yes', 'y'):
        return True
    if s in ('0', 'false', 'no', 'n'):
        return False
    return None


class StockinRefundOpenAPIPullService(BasePullService):
    SERVICE_NAME = 'stockin_refund_openapi'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'wms_stockin_refund_query_with_detail'
    # 文档：start_time / end_time 最大跨度 30 天
    TIME_SPAN_MINUTES = 30 * 24 * 60

    def __init__(self, client: WdtClient = None, repository: OpenapiStockinRefundRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or OpenapiStockinRefundRepository()
        super().__init__(self.client, self.repo)

    @property
    def stockin_refund_openapi_api(self) -> QueryStockinRefundOpenAPI:
        return self.client.stockin_refund_openapi_api

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        debug = kwargs.get('debug', False)
        page_size = kwargs.get('page_size', 200)

        time_type = kwargs.get('time_type')
        if time_type is None or time_type == '':
            time_type = 0
        else:
            time_type = int(time_type)

        shop_nos = kwargs.get('shop_nos') or kwargs.get('shop_no')
        if shop_nos is not None:
            shop_nos = str(shop_nos).strip() or None

        platform_id = kwargs.get('platform_id')
        if platform_id is not None and platform_id != '':
            platform_id = int(platform_id)
        else:
            platform_id = None

        fetch_stock_only = kwargs.get('fetch_stock_only')
        if fetch_stock_only is not None and fetch_stock_only != '':
            fetch_stock_only = int(fetch_stock_only)
        else:
            fetch_stock_only = None

        if debug:
            debug_print(f"    [DEBUG] 调用 API: {self.stockin_refund_openapi_api.METHOD}")

        return self.stockin_refund_openapi_api.query_all(
            start_time=start_time,
            end_time=end_time,
            warehouse_no=kwargs.get('warehouse_no'),
            stockin_no=kwargs.get('stockin_no'),
            refund_no=kwargs.get('refund_no'),
            shop_nos=shop_nos,
            status=kwargs.get('status'),
            time_type=time_type,
            need_sn=_as_bool(kwargs.get('need_sn')),
            need_summary=_as_bool(kwargs.get('need_summary')),
            need_gov_subsidy_info=_as_bool(kwargs.get('need_gov_subsidy_info')),
            fetch_stock_only=fetch_stock_only,
            platform_id=platform_id,
            page_size=page_size,
            debug=debug,
        )
