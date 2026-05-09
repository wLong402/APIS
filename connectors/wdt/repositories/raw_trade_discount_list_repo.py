# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class RawTradeDiscountListRepository(BaseRepository):

    TABLE_NAME = 'raw_trade_discount_list'
    UNIQUE_KEY = 'rec_id'
    SYSTEM_PREFIX = 'wdt'
