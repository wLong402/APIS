# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class LogisticsTraceRepository(BaseRepository):
    TABLE_NAME = 'logistics_trace'
    UNIQUE_KEY = 'rec_id'
    SYSTEM_PREFIX = 'wdt'
