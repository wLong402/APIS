# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class RawTradeDetailRepository(BaseRepository):
    
    TABLE_NAME = 'raw_trade_detail'
    UNIQUE_KEY = 'rec_id'
    SYSTEM_PREFIX = 'wdt'

