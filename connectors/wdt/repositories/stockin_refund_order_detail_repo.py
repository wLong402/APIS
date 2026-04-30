# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class StockinRefundOrderDetailRepository(BaseRepository):
    
    TABLE_NAME = 'stockin_refund_order_detail_tamp2'
    UNIQUE_KEY = ['rec_id', 'refund_order_id']
    SYSTEM_PREFIX = 'wdt'
