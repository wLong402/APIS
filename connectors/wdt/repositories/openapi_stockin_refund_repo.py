# -*- coding: utf-8 -*-
"""OpenAPI 退货入库单入库；结构与奇门版类似，独立表避免混写。"""

import json
from typing import List, Dict

from common.base_repository import BaseRepository


class OpenapiStockinRefundDetailItemRepository(BaseRepository):
    TABLE_NAME = 'openapi_stockin_refund_detail'
    UNIQUE_KEY = 'rec_id'
    SYSTEM_PREFIX = 'wdt'


class OpenapiStockinRefundOrderDetailRepository(BaseRepository):
    TABLE_NAME = 'openapi_stockin_refund_order_detail'
    UNIQUE_KEY = ['rec_id', 'refund_order_id']
    SYSTEM_PREFIX = 'wdt'


class OpenapiStockinRefundRepository(BaseRepository):
    """主表 + details_list + refund_order_detail_list"""

    TABLE_NAME = 'openapi_stockin_refund'
    UNIQUE_KEY = 'stockin_id'
    SYSTEM_PREFIX = 'wdt'

    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.detail_repo = OpenapiStockinRefundDetailItemRepository(db_manager)
        self.order_detail_repo = OpenapiStockinRefundOrderDetailRepository(db_manager)

    def save_batch(self, data_list: List[Dict], batch_size: int = 500,
                   debug: bool = False, progress_label: str = '', **kwargs) -> int:
        if not data_list:
            return 0

        detail_list = []
        order_detail_list = []
        stockin_list = []

        self.logger.info(f"开始处理 {len(data_list)} 条 OpenAPI 退货入库单...")

        for stockin in data_list:
            stockin_id = stockin.get('stockin_id')
            order_no = stockin.get('order_no') or stockin.get('stockin_no')
            details_list = stockin.get('details_list') or []
            if isinstance(details_list, str):
                try:
                    details_list = json.loads(details_list)
                except Exception:
                    details_list = []

            if isinstance(details_list, list):
                for detail in details_list:
                    if not isinstance(detail, dict):
                        continue
                    item = detail.copy()
                    item['stockin_id'] = stockin_id
                    item['order_no'] = order_no
                    item['stockin_no'] = order_no
                    nested = item.pop('refund_order_detail_list', None) or []
                    if isinstance(nested, str):
                        try:
                            nested = json.loads(nested)
                        except Exception:
                            nested = []
                    detail_list.append(item)
                    if isinstance(nested, list):
                        for od in nested:
                            if not isinstance(od, dict):
                                continue
                            od_item = od.copy()
                            od_item['stockin_id'] = stockin_id
                            od_item['order_no'] = order_no
                            od_item['stockin_no'] = order_no
                            od_item['rec_id'] = item.get('rec_id')
                            order_detail_list.append(od_item)

            row = stockin.copy()
            row.pop('details_list', None)
            # 国补嵌套存 JSON
            gov = row.get('gov_subsidy_info')
            if isinstance(gov, (list, dict)):
                row['gov_subsidy_info'] = json.dumps(gov, ensure_ascii=False)
            if not row.get('stockin_no') and order_no:
                row['stockin_no'] = order_no
            stockin_list.append(row)

        count = super().save_batch(
            stockin_list, batch_size, debug=debug, progress_label=progress_label
        )
        if detail_list:
            sub = f"{progress_label}.detail" if progress_label else ""
            self.detail_repo.save_batch(detail_list, batch_size, debug=debug, progress_label=sub)
        if order_detail_list:
            sub = f"{progress_label}.order_detail" if progress_label else ""
            self.order_detail_repo.save_batch(
                order_detail_list, batch_size, debug=debug, progress_label=sub
            )
        return count
