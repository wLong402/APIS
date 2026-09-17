# -*- coding: utf-8 -*-
"""
ERP 订单查询（旗舰 OpenAPI，含明细）

sales.TradeQuery.queryWithDetail
文档: https://open.wangdian.cn/qjb/open/apidoc/doc?path=sales.TradeQuery.queryWithDetail

与奇门版 wdt.sales.tradequery.querywithdetail（服务 erp_trade）不同。
start_time / end_time 最大跨度 60 分钟；page_no 从 0 开始。
"""

from typing import Dict, Optional, List

from ..openapi_client import OpenAPIClient
from ..config import WdtConfig


def _get_debug_print():
    try:
        from utils.logger import debug_print
        return debug_print
    except ImportError:
        return lambda msg, end='\n', flush=False: print(f"    {msg}", end=end, flush=flush)


class QueryTradeWithDetailAPI:
    """
    ERP 订单查询（含明细）OpenAPI

    响应: data.order[]（含嵌套 detail_list）
    """

    METHOD = 'sales.TradeQuery.queryWithDetail'

    def __init__(
        self,
        client: Optional[OpenAPIClient] = None,
        config: Optional[WdtConfig] = None,
        gateway_url: Optional[str] = None,
    ):
        self.client = client or OpenAPIClient(config)
        if gateway_url:
            self.client.GATEWAY_URL = gateway_url

    def query(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        warehouse_no: Optional[str] = None,
        status: Optional[str] = None,
        trade_no: Optional[str] = None,
        shop_no: Optional[str] = None,
        logistics_no: Optional[str] = None,
        src_tid: Optional[str] = None,
        is_slave: Optional[bool] = None,
        cal_share_post_amount: Optional[bool] = None,
        trade_from: Optional[str] = None,
        order_type: Optional[int] = None,
        time_type: int = 1,
        need_gift_relation: int = 1,
        accurate_query: Optional[int] = None,
        cut_logistics_no: Optional[int] = None,
        is_split: Optional[int] = None,
        fenxiao_tid: Optional[str] = None,
        page_size: int = 200,
        page_no: int = 0,
        debug: bool = False,
    ) -> Dict:
        params = {
            'time_type': int(time_type) if time_type is not None else 1,
            'need_gift_relation': int(need_gift_relation) if need_gift_relation is not None else 1,
        }
        if start_time:
            params['start_time'] = start_time
        if end_time:
            params['end_time'] = end_time
        if warehouse_no:
            params['warehouse_no'] = warehouse_no
        if status is not None and status != '':
            params['status'] = str(status)
        if trade_no:
            params['trade_no'] = trade_no
        if shop_no:
            params['shop_no'] = shop_no
        if logistics_no:
            params['logistics_no'] = logistics_no
        if src_tid:
            params['src_tid'] = src_tid
        if is_slave is not None:
            params['is_slave'] = bool(is_slave)
        if cal_share_post_amount is not None:
            params['cal_share_post_amount'] = bool(cal_share_post_amount)
        if trade_from:
            params['trade_from'] = str(trade_from)
        if order_type is not None:
            params['order_type'] = int(order_type)
        if accurate_query is not None:
            params['accurate_query'] = int(accurate_query)
        if cut_logistics_no is not None:
            params['cut_logistics_no'] = int(cut_logistics_no)
        if is_split is not None:
            params['is_split'] = int(is_split)
        if fenxiao_tid:
            params['fenxiao_tid'] = fenxiao_tid

        pager = {'page_size': page_size, 'page_no': page_no, 'calc_total': 1}
        result = self.client.call(self.METHOD, params, pager, debug=debug)

        if debug:
            debug_print = _get_debug_print()
            data = result.get('data', {}) or {}
            orders = data.get('order', []) or []
            debug_print(
                f"    [DEBUG] API响应: status={result.get('status')}, "
                f"total_count={data.get('total_count', 0)}, 本页={len(orders)}条"
            )
        return result

    def query_all(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        warehouse_no: Optional[str] = None,
        status: Optional[str] = None,
        trade_no: Optional[str] = None,
        shop_no: Optional[str] = None,
        logistics_no: Optional[str] = None,
        src_tid: Optional[str] = None,
        is_slave: Optional[bool] = None,
        cal_share_post_amount: Optional[bool] = None,
        trade_from: Optional[str] = None,
        order_type: Optional[int] = None,
        time_type: int = 1,
        need_gift_relation: int = 1,
        accurate_query: Optional[int] = None,
        cut_logistics_no: Optional[int] = None,
        is_split: Optional[int] = None,
        fenxiao_tid: Optional[str] = None,
        page_size: int = 200,
        debug: bool = False,
    ) -> List[Dict]:
        """从最后一页往前翻，避免增量窗口内漏单。"""
        debug_print = _get_debug_print()
        common = dict(
            start_time=start_time,
            end_time=end_time,
            warehouse_no=warehouse_no,
            status=status,
            trade_no=trade_no,
            shop_no=shop_no,
            logistics_no=logistics_no,
            src_tid=src_tid,
            is_slave=is_slave,
            cal_share_post_amount=cal_share_post_amount,
            trade_from=trade_from,
            order_type=order_type,
            time_type=time_type,
            need_gift_relation=need_gift_relation,
            accurate_query=accurate_query,
            cut_logistics_no=cut_logistics_no,
            is_split=is_split,
            fenxiao_tid=fenxiao_tid,
            page_size=page_size,
        )

        first = self.query(page_no=0, debug=debug, **common)
        if str(first.get('status')) != '0':
            if debug:
                debug_print(f"    [DEBUG] API错误: {first.get('message')}")
            return []

        data = first.get('data', {}) or {}
        total_count = int(data.get('total_count', 0) or 0)
        if debug:
            debug_print(f"    [DEBUG] 总数: {total_count}")
        if total_count == 0:
            return []

        total_pages = (total_count + page_size - 1) // page_size
        all_orders: List[Dict] = []
        seen_ids = set()

        for page_no in range(total_pages - 1, -1, -1):
            if debug:
                debug_print(f"    [DEBUG] 请求第 {page_no + 1}/{total_pages} 页（从后往前）...")
            result = self.query(page_no=page_no, debug=False, **common)
            if str(result.get('status')) != '0':
                if debug:
                    debug_print(f"    [DEBUG] 第 {page_no + 1} 页失败: {result.get('message')}")
                continue
            for order in (result.get('data', {}) or {}).get('order', []) or []:
                if not isinstance(order, dict):
                    continue
                key = order.get('trade_id')
                if key is not None:
                    if key in seen_ids:
                        continue
                    seen_ids.add(key)
                all_orders.append(order)

        if debug:
            debug_print(f"    [DEBUG] 共获取 {len(all_orders)} 条订单")
        return all_orders
