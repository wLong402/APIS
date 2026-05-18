# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ExpenseSkuShareDayDetailRepository(BaseRepository):
    TABLE_NAME = 'expense_sku_share_day_detail'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
