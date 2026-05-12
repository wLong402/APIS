# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ReconDeliveryDetailRepository(BaseRepository):
    TABLE_NAME = 'recon_delivery_detail'
    UNIQUE_KEY = 'detailId'
    SYSTEM_PREFIX = 'wdt'
