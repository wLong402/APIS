# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class HjyDeliveryDetailRepository(BaseRepository):
    """慧经营发货明细；UK=detailId"""

    TABLE_NAME = 'hjy_delivery_detail'
    UNIQUE_KEY = 'detailId'
    SYSTEM_PREFIX = 'wdt'
