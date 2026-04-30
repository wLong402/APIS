# -*- coding: utf-8 -*-

import json
from typing import List, Dict

from common.base_repository import BaseRepository
from .stockout_sales_detail_repo import StockoutSalesDetailItemRepository


class StockoutSalesDetailRepository(BaseRepository):
    
    TABLE_NAME = 'stockout_sales'
    UNIQUE_KEY = 'stockout_id'
    SYSTEM_PREFIX = 'wdt'
    
    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.detail_item_repo = StockoutSalesDetailItemRepository(db_manager)
    
    def save_batch(self, data_list: List[Dict], batch_size: int = 500) -> int:
        if not data_list:
            return 0
        
        detail_item_list = []
        stockout_list = []
        
        self.logger.info(f"开始处理 {len(data_list)} 条出库单，提取明细...")
        
        for stockout in data_list:
            stockout_no = stockout.get('stockout_no') or stockout.get('stockout_id')
            details_list_field = stockout.get('details_list') or stockout.get('detail_list') or stockout.get('order_detail_list') or []
            
            if isinstance(details_list_field, str):
                try:
                    details_list_field = json.loads(details_list_field)
                except:
                    details_list_field = []
            
            if isinstance(details_list_field, list) and stockout_no:
                for detail in details_list_field:
                    if isinstance(detail, dict):
                        detail_item = detail.copy()
                        detail_item['stockout_no'] = stockout_no
                        detail_item_list.append(detail_item)
            
            stockout_copy = stockout.copy()
            for key in ['details_list', 'detail_list', 'order_detail_list']:
                if key in stockout_copy:
                    del stockout_copy[key]
            stockout_list.append(stockout_copy)
        
        self.logger.info(f"提取到 {len(detail_item_list)} 条明细，开始保存出库单...")
        count = super().save_batch(stockout_list, batch_size)
        
        if detail_item_list:
            self.logger.info(f"开始保存 {len(detail_item_list)} 条出库单明细...")
            self.detail_item_repo.save_batch(detail_item_list, batch_size)
            self.logger.info(f"保存出库单明细完成")
        
        return count
