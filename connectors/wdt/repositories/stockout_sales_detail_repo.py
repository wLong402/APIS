# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class StockoutSalesDetailItemRepository(BaseRepository):
    
    TABLE_NAME = 'stockout_sales_detail'
    UNIQUE_KEY = 'rec_id'
    SYSTEM_PREFIX = 'wdt'
