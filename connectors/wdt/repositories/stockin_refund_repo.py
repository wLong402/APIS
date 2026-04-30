# -*- coding: utf-8 -*-

import json
from typing import List, Dict

from common.base_repository import BaseRepository
from .stockin_refund_detail_repo import StockinRefundDetailItemRepository
from .stockin_refund_order_detail_repo import StockinRefundOrderDetailRepository


class StockinRefundDetailRepository(BaseRepository):
    
    TABLE_NAME = 'stockin_refund_tamp2'
    UNIQUE_KEY = ['refund_no','order_no']
    SYSTEM_PREFIX = 'wdt'
    
    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.detail_repo = StockinRefundDetailItemRepository(db_manager)
        self.order_detail_repo = StockinRefundOrderDetailRepository(db_manager)
    
    def save_batch(self, data_list: List[Dict], batch_size: int = 500) -> int:
        if not data_list:
            return 0
        
        detail_list = []
        order_detail_list = []
        stockin_list = []
        
        self.logger.info(f"开始处理 {len(data_list)} 条入库单，提取明细...")
        
        for stockin in data_list:
            stockin_no = stockin.get('stockin_no') or stockin.get('stockin_id')
            details_list = stockin.get('details_list') or []
            
            if isinstance(details_list, str):
                try:
                    details_list = json.loads(details_list)
                except:
                    details_list = []
            
            if isinstance(details_list, list) and stockin_no:
                for detail in details_list:
                    if isinstance(detail, dict):
                        detail_item = detail.copy()
                        detail_item['stockin_no'] = stockin_no
                        
                        refund_order_detail_list = detail_item.pop('refund_order_detail_list', None) or []
                        if isinstance(refund_order_detail_list, str):
                            try:
                                refund_order_detail_list = json.loads(refund_order_detail_list)
                            except:
                                refund_order_detail_list = []
                        
                        detail_list.append(detail_item)
                        
                        if isinstance(refund_order_detail_list, list):
                            for od in refund_order_detail_list:
                                if isinstance(od, dict):
                                    od_item = od.copy()
                                    od_item['stockin_no'] = stockin_no
                                    od_item['rec_id'] = detail_item.get('rec_id')
                                    order_detail_list.append(od_item)
            
            stockin_copy = stockin.copy()
            if 'details_list' in stockin_copy:
                del stockin_copy['details_list']
            stockin_list.append(stockin_copy)
        
        self.logger.info(f"提取到 {len(detail_list)} 条明细, {len(order_detail_list)} 条退款订单明细，开始保存入库单...")
        count = super().save_batch(stockin_list, batch_size)
        
        if detail_list:
            self.logger.info(f"开始保存 {len(detail_list)} 条入库单明细...")
            self.detail_repo.save_batch(detail_list, batch_size)
            self.logger.info(f"保存入库单明细完成")
        
        if order_detail_list:
            self.logger.info(f"开始保存 {len(order_detail_list)} 条退款订单明细...")
            self.order_detail_repo.save_batch(order_detail_list, batch_size)
            self.logger.info(f"保存退款订单明细完成")
        
        return count
