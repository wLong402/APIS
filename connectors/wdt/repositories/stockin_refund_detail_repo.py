# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class StockinRefundDetailItemRepository(BaseRepository):
    
    TABLE_NAME = 'stockin_refund_detail_tamp2'
    UNIQUE_KEY = 'rec_id'
    SYSTEM_PREFIX = 'wdt'
