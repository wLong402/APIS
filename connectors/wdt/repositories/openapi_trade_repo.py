# -*- coding: utf-8 -*-
"""OpenAPI ERP 订单入库；与奇门 wdt_erp_trade 分表。"""

import json
from typing import List, Dict

from common.base_repository import BaseRepository


class OpenapiTradeDetailRepository(BaseRepository):
    TABLE_NAME = 'openapi_trade_detail'
    UNIQUE_KEY = 'rec_id'
    SYSTEM_PREFIX = 'wdt'


class OpenapiTradeRepository(BaseRepository):
    """主表 + detail_list"""

    TABLE_NAME = 'openapi_trade'
    UNIQUE_KEY = 'trade_id'
    SYSTEM_PREFIX = 'wdt'

    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.detail_repo = OpenapiTradeDetailRepository(db_manager)

    def save_batch(self, data_list: List[Dict], batch_size: int = 500,
                   debug: bool = False, progress_label: str = '', **kwargs) -> int:
        if not data_list:
            return 0

        trade_list = []
        detail_list = []

        self.logger.info(f"开始处理 {len(data_list)} 条 OpenAPI 订单，提取明细...")

        for trade in data_list:
            trade_id = trade.get('trade_id')
            trade_no = trade.get('trade_no')
            nested = trade.get('detail_list') or []
            if isinstance(nested, str):
                try:
                    nested = json.loads(nested)
                except Exception:
                    nested = []

            if isinstance(nested, list):
                for detail in nested:
                    if not isinstance(detail, dict):
                        continue
                    item = detail.copy()
                    if trade_id is not None:
                        item['trade_id'] = trade_id
                    if trade_no:
                        item['trade_no'] = trade_no
                    detail_list.append(item)

            row = trade.copy()
            row.pop('detail_list', None)
            trade_list.append(row)

        count = super().save_batch(
            trade_list, batch_size, debug=debug, progress_label=progress_label
        )
        if detail_list:
            sub = f"{progress_label}.detail" if progress_label else ""
            self.detail_repo.save_batch(detail_list, batch_size, debug=debug, progress_label=sub)
        return count
