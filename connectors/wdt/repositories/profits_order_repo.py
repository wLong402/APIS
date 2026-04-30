# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ProfitsOrderRepository(BaseRepository):
    TABLE_NAME = 'profits_order'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
