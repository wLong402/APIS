# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ProfitsLiveSkuRepository(BaseRepository):
    TABLE_NAME = 'profits_live_sku'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
