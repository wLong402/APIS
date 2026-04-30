# -*- coding: utf-8 -*-
"""
原始订单数据仓库
"""

import json
from typing import List, Dict

from common.base_repository import BaseRepository
from .raw_trade_detail_repo import RawTradeDetailRepository


class TradeRepository(BaseRepository):
    """原始订单数据仓库"""
    
    TABLE_NAME = 'raw_trade'
    UNIQUE_KEY = 'rec_id'
    SYSTEM_PREFIX = 'wdt'
    
    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.detail_repo = RawTradeDetailRepository(db_manager)
    
    def save_batch(self, data_list: List[Dict], batch_size: int = 500) -> int:
        """批量保存订单数据，同时保存明细"""
        if not data_list:
            return 0
        
        detail_list = []
        trade_list = []
        
        self.logger.info(f"开始处理 {len(data_list)} 条订单，提取明细...")
        
        for trade in data_list:
            tid = trade.get('tid') or trade.get('rec_id')
            trade_orders_field = trade.get('trade_orders') or []
            
            if isinstance(trade_orders_field, str):
                try:
                    trade_orders_field = json.loads(trade_orders_field)
                except:
                    trade_orders_field = []
            
            if isinstance(trade_orders_field, list) and tid:
                for order in trade_orders_field:
                    if isinstance(order, dict):
                        detail_item = order.copy()
                        detail_item['tid'] = tid
                        detail_list.append(detail_item)
            
            trade_copy = trade.copy()
            if 'trade_orders' in trade_copy:
                del trade_copy['trade_orders']
            trade_list.append(trade_copy)
        
        self.logger.info(f"提取到 {len(detail_list)} 条明细，开始保存订单...")
        count = super().save_batch(trade_list, batch_size)
        
        if detail_list:
            self.logger.info(f"开始保存 {len(detail_list)} 条订单明细...")
            try:
                detail_count = self.detail_repo.save_batch(detail_list, batch_size)
                self.logger.info(f"保存订单明细完成: {detail_count} 条")
            except Exception as e:
                self.logger.error(f"保存订单明细失败: {e}", exc_info=True)
                raise
        
        return count

