# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ProfitsLiveRefundRepository(BaseRepository):
    TABLE_NAME = 'profits_live_refund'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
