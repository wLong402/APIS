# -*- coding: utf-8 -*-

from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import StockoutSalesDetailRepository
from ..sdk.api import StockoutStatusType


class StockoutSalesQueryWithDetailPullService(BasePullService):
    
    SERVICE_NAME = 'stockout_sales_query_with_detail'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'stockout_sales_query_with_detail'
    TIME_SPAN_MINUTES = 60
    
    def __init__(self, client: WdtClient = None, repository: StockoutSalesDetailRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or StockoutSalesDetailRepository()
        super().__init__(self.client, self.repo)
    
    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        debug = kwargs.get('debug', False)
        page_size = kwargs.get('page_size', 200)
        
        if debug:
            print(f"    [DEBUG] 请求: {start_time} ~ {end_time}")
            print(f"    [DEBUG] 调用 API: {self.client.stockout_sales_query_with_detail_api.METHOD}")
        
        first_result = self.client.stockout_sales_query_with_detail_api.query(
            start_time=start_time,
            end_time=end_time,
            status_type=kwargs.get('status_type', StockoutStatusType.DELAYED_AND_COMPLETED),
            status=kwargs.get('status'),
            warehouse_no=kwargs.get('warehouse_no'),
            shop_nos=kwargs.get('shop_nos'),
            page_size=page_size,
            page_no=1,
            debug=debug
        )
        
        if str(first_result.get('status')) != '0':
            if debug:
                print(f"    [DEBUG] API错误: {first_result.get('message')}")
            return []
        
        data = first_result.get('data', {})
        total_count = int(data.get('total_count', 0))
        first_orders = data.get('order', [])
        
        if debug:
            print(f"    [DEBUG] 总数: {total_count}, 第1页: {len(first_orders)}条")
        
        if total_count == 0:
            return []
        
        total_pages = (total_count + page_size - 1) // page_size
        
        if total_pages == 1:
            if debug and first_orders:
                print(f"    [DEBUG] 第一条数据的字段: {list(first_orders[0].keys())}")
            return first_orders
        
        all_stockouts = list(first_orders)
        
        for page_no in range(2, total_pages + 1):
            if debug:
                print(f"    [DEBUG] 请求第 {page_no}/{total_pages} 页...")
            
            result = self.client.stockout_sales_query_with_detail_api.query(
                start_time=start_time,
                end_time=end_time,
                status_type=kwargs.get('status_type', StockoutStatusType.DELAYED_AND_COMPLETED),
                status=kwargs.get('status'),
                warehouse_no=kwargs.get('warehouse_no'),
                shop_nos=kwargs.get('shop_nos'),
                page_size=page_size,
                page_no=page_no,
                debug=False
            )
            
            if str(result.get('status')) == '0':
                stockouts = result.get('data', {}).get('order', [])
                all_stockouts.extend(stockouts)
        
        if debug:
            print(f"    [DEBUG] 共获取 {len(all_stockouts)} 条")
        
        return all_stockouts
