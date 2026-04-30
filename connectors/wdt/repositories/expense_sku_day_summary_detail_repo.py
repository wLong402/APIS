# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ExpenseSkuDaySummaryDetailRepository(BaseRepository):
    TABLE_NAME = 'expense_sku_day_summary_detail'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
