# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class RawRefundDetailRepository(BaseRepository):
    
    TABLE_NAME = 'raw_refund_detail'
    UNIQUE_KEY = 'rec_id'
    SYSTEM_PREFIX = 'wdt'
