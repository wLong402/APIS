# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ProfitsSkuRepository(BaseRepository):
    TABLE_NAME = 'profits_sku'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
