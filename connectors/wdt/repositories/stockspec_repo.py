# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class StockSpecRepository(BaseRepository):
    
    TABLE_NAME = 'stockspec'
    UNIQUE_KEY = 'spec_id'
    SYSTEM_PREFIX = 'wdt'

