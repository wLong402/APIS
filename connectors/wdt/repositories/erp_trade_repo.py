# -*- coding: utf-8 -*-
"""
ERP订单数据仓库
"""

import json
from typing import List, Dict

from common.base_repository import BaseRepository
from .erp_trade_detail_repo import ErpTradeDetailRepository


class ErpTradeRepository(BaseRepository):
    """ERP订单数据仓库"""
    
    TABLE_NAME = 'erp_trade'
    UNIQUE_KEY = 'trade_id'
    SYSTEM_PREFIX = 'wdt'
    
    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.detail_repo = ErpTradeDetailRepository(db_manager)
    
    def save_batch(self, data_list: List[Dict], batch_size: int = 500, debug: bool = False, progress_label: str = '', **kwargs) -> int:
        """批量保存订单数据，同时保存明细"""
        if not data_list:
            return 0
        
        detail_list = []
        trade_list = []
        
        self.logger.info(f"开始处理 {len(data_list)} 条订单，提取明细...")
        
        for trade in data_list:
            trade_no = trade.get('trade_no') or trade.get('trade_id')
            detail_list_field = trade.get('detail_list') or trade.get('order_detail_list') or []
            
            if isinstance(detail_list_field, str):
                try:
                    detail_list_field = json.loads(detail_list_field)
                except:
                    detail_list_field = []
            
            if isinstance(detail_list_field, list) and trade_no:
                for detail in detail_list_field:
                    if isinstance(detail, dict):
                        detail_item = detail.copy()
                        detail_item['trade_no'] = trade_no
                        detail_list.append(detail_item)
            
            trade_copy = trade.copy()
            if 'detail_list' in trade_copy:
                del trade_copy['detail_list']
            if 'order_detail_list' in trade_copy:
                del trade_copy['order_detail_list']
            trade_list.append(trade_copy)
        
        self.logger.info(f"提取到 {len(detail_list)} 条明细，开始保存订单...")
        count = super().save_batch(trade_list, batch_size, debug=debug, progress_label=progress_label)
        
        if detail_list:
            self.logger.info(f"开始保存 {len(detail_list)} 条订单明细...")
            try:
                sub_lbl = f"{progress_label}.detail" if progress_label else ""
                detail_count = self.detail_repo.save_batch(detail_list, batch_size, debug=debug, progress_label=sub_lbl)
                self.logger.info(f"保存订单明细完成: {detail_count} 条")
            except Exception as e:
                self.logger.error(f"保存订单明细失败: {e}", exc_info=True)
                raise
        
        return count

