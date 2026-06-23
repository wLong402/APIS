# -*- coding: utf-8 -*-

from typing import Dict, Optional, List
from ..openapi_client import OpenAPIClient
from ..config import WdtConfig


def _get_debug_print():
    try:
        from utils.logger import debug_print
        return debug_print
    except ImportError:
        return lambda msg, end='\n', flush=False: print(f"    {msg}", end=end, flush=flush)


class SearchLogisticsTraceAPI:
    METHOD = 'statistic.GoodsSendStatistic.searchLogisticsTrace'

    def __init__(self, client: Optional[OpenAPIClient] = None,
                 config: Optional[WdtConfig] = None,
                 gateway_url: Optional[str] = None):
        self.client = client or OpenAPIClient(config)
        if gateway_url:
            self.client.GATEWAY_URL = gateway_url

    def search(self,
               start_time: Optional[str] = None,
               end_time: Optional[str] = None,
               logistics_status: Optional[int] = None,
               warehouse_no: Optional[str] = None,
               shop_no: Optional[str] = None,
               need_detail: bool = False,
               logistics_no: Optional[str] = None,
               page_size: int = 200,
               page_no: int = 0,
               debug: bool = False) -> Dict:
        params = {}
        if logistics_no:
            params['logistics_no'] = logistics_no
        else:
            if start_time:
                params['start_time'] = start_time
            if end_time:
                params['end_time'] = end_time
            if logistics_status is not None:
                params['logistics_status'] = logistics_status
            else:
                params['logistics_status'] = 5
        if warehouse_no:
            params['warehouse_no'] = warehouse_no
        if shop_no:
            params['shop_no'] = shop_no
        if need_detail:
            params['need_detail'] = True

        pager = {'page_size': page_size, 'page_no': page_no, 'calc_total': 1}
        result = self.client.call(self.METHOD, params, pager, debug=debug)

        if debug:
            debug_print = _get_debug_print()
            status_code = result.get('status')
            data = result.get('data', {})
            total = data.get('total_count', 0)
            orders = data.get('order_list', [])
            debug_print(f"    [DEBUG] API响应: status={status_code}, total_count={total}, 本页={len(orders)}条")

        return result

    def search_all(self,
                   start_time: Optional[str] = None,
                   end_time: Optional[str] = None,
                   logistics_status: Optional[int] = None,
                   warehouse_no: Optional[str] = None,
                   shop_no: Optional[str] = None,
                   need_detail: bool = False,
                   logistics_no: Optional[str] = None,
                   page_size: int = 200,
                   debug: bool = False) -> List[Dict]:
        debug_print = _get_debug_print()
        if need_detail and page_size > 100:
            page_size = 100

        first_result = self.search(
            start_time=start_time,
            end_time=end_time,
            logistics_status=logistics_status,
            warehouse_no=warehouse_no,
            shop_no=shop_no,
            need_detail=need_detail,
            logistics_no=logistics_no,
            page_size=page_size,
            page_no=0,
            debug=debug,
        )

        if str(first_result.get('status')) != '0':
            if debug:
                msg = first_result.get('message') or first_result.get('code') or first_result
                debug_print(f"    [DEBUG] API错误: status={first_result.get('status')} {msg}")
            return []

        data = first_result.get('data', {})
        total_count = int(data.get('total_count', 0))
        first_orders = data.get('order_list', [])

        if debug:
            debug_print(f"    [DEBUG] 总数: {total_count}, 第1页: {len(first_orders)}条")

        if total_count == 0:
            return []

        total_pages = (total_count + page_size - 1) // page_size
        if total_pages == 1:
            return first_orders

        all_orders = list(first_orders)
        for page_no in range(1, total_pages):
            if debug:
                debug_print(f"    [DEBUG] 请求第 {page_no + 1}/{total_pages} 页...")
            result = self.search(
                start_time=start_time,
                end_time=end_time,
                logistics_status=logistics_status,
                warehouse_no=warehouse_no,
                shop_no=shop_no,
                need_detail=need_detail,
                logistics_no=logistics_no,
                page_size=page_size,
                page_no=page_no,
                debug=False,
            )
            if str(result.get('status')) == '0':
                all_orders.extend(result.get('data', {}).get('order_list', []))

        if debug:
            debug_print(f"    [DEBUG] 共获取 {len(all_orders)} 条")
        return all_orders
