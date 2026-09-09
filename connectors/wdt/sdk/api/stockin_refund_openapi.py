# -*- coding: utf-8 -*-
"""
退货入库单查询（旗舰 OpenAPI）

wms.stockin.Refund.queryWithDetail
文档: https://open.wangdian.cn/qjb/open/apidoc/doc?path=wms.stockin.Refund.queryWithDetail

与奇门版 wdt.wms.stockin.refund.querywithdetail 不同。
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


class QueryStockinRefundOpenAPI:
    """
    退货入库单查询（含明细）OpenAPI

    start_time / end_time 最大跨度 30 天；page_no 从 0 开始。
    响应: data.order[]（含 details_list / refund_order_detail_list）
    """

    METHOD = 'wms.stockin.Refund.queryWithDetail'

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
        start_time: str,
        end_time: str,
        warehouse_no: Optional[str] = None,
        stockin_no: Optional[str] = None,
        refund_no: Optional[str] = None,
        shop_nos: Optional[str] = None,
        status: Optional[str] = None,
        time_type: int = 0,
        need_sn: Optional[bool] = None,
        need_summary: Optional[bool] = None,
        need_gov_subsidy_info: Optional[bool] = None,
        fetch_stock_only: Optional[int] = None,
        platform_id: Optional[int] = None,
        page_size: int = 200,
        page_no: int = 0,
        debug: bool = False,
    ) -> Dict:
        params = {
            'start_time': start_time,
            'end_time': end_time,
            'time_type': int(time_type) if time_type is not None else 0,
        }
        if warehouse_no:
            params['warehouse_no'] = warehouse_no
        if stockin_no:
            params['stockin_no'] = stockin_no
        if refund_no:
            params['refund_no'] = refund_no
        if shop_nos:
            params['shop_nos'] = shop_nos
        if status is not None and status != '':
            params['status'] = str(status)
        if need_sn is not None:
            params['need_sn'] = bool(need_sn)
        if need_summary is not None:
            params['need_summary'] = bool(need_summary)
        if need_gov_subsidy_info is not None:
            params['need_gov_subsidy_info'] = bool(need_gov_subsidy_info)
        if fetch_stock_only is not None:
            params['fetch_stock_only'] = int(fetch_stock_only)
        if platform_id is not None:
            params['platform_id'] = int(platform_id)

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
        start_time: str,
        end_time: str,
        warehouse_no: Optional[str] = None,
        stockin_no: Optional[str] = None,
        refund_no: Optional[str] = None,
        shop_nos: Optional[str] = None,
        status: Optional[str] = None,
        time_type: int = 0,
        need_sn: Optional[bool] = None,
        need_summary: Optional[bool] = None,
        need_gov_subsidy_info: Optional[bool] = None,
        fetch_stock_only: Optional[int] = None,
        platform_id: Optional[int] = None,
        page_size: int = 200,
        debug: bool = False,
    ) -> List[Dict]:
        debug_print = _get_debug_print()
        first = self.query(
            start_time=start_time,
            end_time=end_time,
            warehouse_no=warehouse_no,
            stockin_no=stockin_no,
            refund_no=refund_no,
            shop_nos=shop_nos,
            status=status,
            time_type=time_type,
            need_sn=need_sn,
            need_summary=need_summary,
            need_gov_subsidy_info=need_gov_subsidy_info,
            fetch_stock_only=fetch_stock_only,
            platform_id=platform_id,
            page_size=page_size,
            page_no=0,
            debug=debug,
        )
        if str(first.get('status')) != '0':
            if debug:
                debug_print(f"    [DEBUG] API错误: {first.get('message')}")
            return []

        data = first.get('data', {}) or {}
        total_count = int(data.get('total_count', 0) or 0)
        first_list = data.get('order', []) or []
        if debug:
            debug_print(f"    [DEBUG] 总数: {total_count}, 第1页: {len(first_list)}条")
        if total_count == 0:
            return []

        total_pages = (total_count + page_size - 1) // page_size
        if total_pages <= 1:
            return first_list

        all_orders = list(first_list)
        for page_no in range(1, total_pages):
            if debug:
                debug_print(f"    [DEBUG] 请求第 {page_no + 1}/{total_pages} 页...")
            result = self.query(
                start_time=start_time,
                end_time=end_time,
                warehouse_no=warehouse_no,
                stockin_no=stockin_no,
                refund_no=refund_no,
                shop_nos=shop_nos,
                status=status,
                time_type=time_type,
                need_sn=need_sn,
                need_summary=need_summary,
                need_gov_subsidy_info=need_gov_subsidy_info,
                fetch_stock_only=fetch_stock_only,
                platform_id=platform_id,
                page_size=page_size,
                page_no=page_no,
                debug=False,
            )
            if str(result.get('status')) == '0':
                all_orders.extend((result.get('data', {}) or {}).get('order', []) or [])

        if debug:
            debug_print(f"    [DEBUG] 共获取 {len(all_orders)} 条入库单")
        return all_orders
