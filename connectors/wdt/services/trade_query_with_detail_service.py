# -*- coding: utf-8 -*-
"""ERP 订单拉取（旗舰 OpenAPI sales.TradeQuery.queryWithDetail）"""

from datetime import datetime
from typing import List, Dict, Optional

from core.logger import debug_print
from common.base_service import BasePullService, PullResult
from ..client import WdtClient, get_wdt_client
from ..repositories.openapi_trade_repo import OpenapiTradeRepository
from ..sdk.api.trade_query_with_detail import QueryTradeWithDetailAPI


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


def _as_int(val, default=None):
    if val is None or val == '':
        return default
    return int(val)


class TradeQueryWithDetailPullService(BasePullService):
    SERVICE_NAME = 'trade_query_with_detail'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'sales_trade_query_with_detail'
    # 文档：start_time / end_time 最大跨度 60 分钟
    TIME_SPAN_MINUTES = 60

    def __init__(self, client: WdtClient = None, repository: OpenapiTradeRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or OpenapiTradeRepository()
        super().__init__(self.client, self.repo)

    @property
    def trade_query_with_detail_api(self) -> QueryTradeWithDetailAPI:
        return self.client.trade_query_with_detail_api

    def pull(self, start_time: str, end_time: str, **kwargs) -> PullResult:
        try:
            start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return super().pull(start_time, end_time, **kwargs)
        if (end_dt - start_dt).total_seconds() > self.TIME_SPAN_MINUTES * 60:
            debug = kwargs.pop('debug', False)
            return self.pull_by_interval(
                start_time,
                end_time,
                interval_seconds=self.TIME_SPAN_MINUTES * 60,
                debug=debug,
                **kwargs,
            )
        return super().pull(start_time, end_time, **kwargs)

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        debug = kwargs.get('debug', False)
        page_size = kwargs.get('page_size', 200)

        time_type = _as_int(kwargs.get('time_type'), 1)
        need_gift_relation = _as_int(kwargs.get('need_gift_relation'), 1)
        order_type = _as_int(kwargs.get('order_type'))
        accurate_query = _as_int(kwargs.get('accurate_query'))
        cut_logistics_no = _as_int(kwargs.get('cut_logistics_no'))
        is_split = _as_int(kwargs.get('is_split'))

        shop_no = kwargs.get('shop_no')
        if shop_no is not None:
            shop_no = str(shop_no).strip() or None

        trade_no = kwargs.get('trade_no') or kwargs.get('erp_order_nos')
        src_tid = kwargs.get('src_tid') or kwargs.get('plat_order_nos')

        if debug:
            debug_print(f"    [DEBUG] 调用 API: {self.trade_query_with_detail_api.METHOD}")

        return self.trade_query_with_detail_api.query_all(
            start_time=start_time,
            end_time=end_time,
            warehouse_no=kwargs.get('warehouse_no'),
            status=kwargs.get('status'),
            trade_no=trade_no,
            shop_no=shop_no,
            logistics_no=kwargs.get('logistics_no'),
            src_tid=src_tid,
            is_slave=_as_bool(kwargs.get('is_slave')),
            cal_share_post_amount=_as_bool(kwargs.get('cal_share_post_amount')),
            trade_from=kwargs.get('trade_from'),
            order_type=order_type,
            time_type=time_type,
            need_gift_relation=need_gift_relation,
            accurate_query=accurate_query,
            cut_logistics_no=cut_logistics_no,
            is_split=is_split,
            fenxiao_tid=kwargs.get('fenxiao_tid'),
            page_size=page_size,
            debug=debug,
        )
