# -*- coding: utf-8 -*-

import json
from typing import List, Dict

from common.base_repository import BaseRepository
from .aftersales_refund_detail_repo import AftersalesRefundDetailRepository


class AftersalesRefundRepository(BaseRepository):
    
    TABLE_NAME = 'aftersales_refund'
    UNIQUE_KEY = 'refund_id'
    SYSTEM_PREFIX = 'wdt'
    
    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.detail_repo = AftersalesRefundDetailRepository(db_manager)
    
    def save_batch(self, data_list: List[Dict], batch_size: int = 500, debug: bool = False, progress_label: str = '', **kwargs) -> int:
        if not data_list:
            return 0
        
        detail_list = []
        refund_list = []
        
        self.logger.info(f"开始处理 {len(data_list)} 条售后退款单，提取明细...")
        
        for refund in data_list:
            refund_id = refund.get('refund_id') or refund.get('refund_no')
            details_list_field = refund.get('detail_list') or refund.get('details_list') or []
            
            if isinstance(details_list_field, str):
                try:
                    details_list_field = json.loads(details_list_field)
                except:
                    details_list_field = []
            
            if isinstance(details_list_field, list) and refund_id:
                for detail in details_list_field:
                    if isinstance(detail, dict):
                        detail_item = detail.copy()
                        detail_item['refund_id'] = refund_id
                        detail_list.append(detail_item)
            
            refund_copy = refund.copy()
            for key in ['detail_list', 'details_list']:
                if key in refund_copy:
                    del refund_copy[key]
            refund_list.append(refund_copy)
        
        self.logger.info(f"提取到 {len(detail_list)} 条明细，开始保存售后退款单...")
        count = super().save_batch(refund_list, batch_size, debug=debug, progress_label=progress_label)
        
        if detail_list:
            self.logger.info(f"开始保存 {len(detail_list)} 条售后退款单明细...")
            sub_lbl = f"{progress_label}.detail" if progress_label else ""
            self.detail_repo.save_batch(detail_list, batch_size, debug=debug, progress_label=sub_lbl)
            self.logger.info(f"保存售后退款单明细完成")
        
        return count
