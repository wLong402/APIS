# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ProfitsLiveOrderRepository(BaseRepository):
    TABLE_NAME = 'profits_live_order'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
