# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class MarketingShareResultRepository(BaseRepository):
    TABLE_NAME = 'marketing_share_result'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
