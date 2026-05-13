# -*- coding: utf-8 -*-

import hashlib
import json
from typing import List, Dict

from common.base_repository import BaseRepository
from .expense_sku_day_summary_detail_repo import ExpenseSkuDaySummaryDetailRepository


class ExpenseSkuDaySummaryRepository(BaseRepository):
    TABLE_NAME = 'expense_sku_day_summary'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'

    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.detail_repo = ExpenseSkuDaySummaryDetailRepository(db_manager)

    @staticmethod
    def _hash(item: Dict) -> str:
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def save_batch(self, data_list: List[Dict], batch_size: int = 500, debug: bool = False, progress_label: str = '', **kwargs) -> int:
        if not data_list:
            return 0

        detail_list = []
        master_list = []

        self.logger.info(f"开始处理 {len(data_list)} 条账单商品分摊日汇总，提取明细...")

        for master in data_list:
            sub_items = master.get('detailList') or master.get('detail_list') or []
            if isinstance(sub_items, str):
                try:
                    sub_items = json.loads(sub_items)
                except Exception:
                    sub_items = []

            master_copy = master.copy()
            for k in ('detailList', 'detail_list'):
                master_copy.pop(k, None)
            if 'rowKey' not in master_copy:
                master_copy['rowKey'] = self._hash(master_copy)
            master_summary_no = master_copy.get('summaryNo')
            master_row_key = master_copy['rowKey']
            master_list.append(master_copy)

            if isinstance(sub_items, list):
                for d in sub_items:
                    if not isinstance(d, dict):
                        continue
                    d_copy = d.copy()
                    if master_summary_no and not d_copy.get('summaryNo'):
                        d_copy['summaryNo'] = master_summary_no
                    d_copy['parentRowKey'] = master_row_key
                    if 'rowKey' not in d_copy:
                        d_copy['rowKey'] = self._hash(d_copy)
                    detail_list.append(d_copy)

        self.logger.info(f"提取到 {len(detail_list)} 条明细，开始保存主单...")
        count = super().save_batch(master_list, batch_size, debug=debug, progress_label=progress_label)

        if detail_list:
            self.logger.info(f"开始保存 {len(detail_list)} 条明细...")
            sub_lbl = f"{progress_label}.detail" if progress_label else ""
            self.detail_repo.save_batch(detail_list, batch_size, debug=debug, progress_label=sub_lbl)
            self.logger.info(f"保存账单商品分摊日汇总明细完成")

        return count
