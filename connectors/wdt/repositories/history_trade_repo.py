# -*- coding: utf-8 -*-
from common.base_repository import BaseRepository


class HistoryTradeRepository(BaseRepository):
    TABLE_NAME = 'history_trade'
    UNIQUE_KEY = 'trade_id'
    SYSTEM_PREFIX = 'wdt'




