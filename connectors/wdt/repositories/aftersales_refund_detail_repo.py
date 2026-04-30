# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class AftersalesRefundDetailRepository(BaseRepository):
    
    TABLE_NAME = 'aftersales_refund_detail'
    UNIQUE_KEY = 'rec_id'
    SYSTEM_PREFIX = 'wdt'
