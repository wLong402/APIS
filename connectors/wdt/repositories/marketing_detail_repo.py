# -*- coding: utf-8 -*-
from common.base_repository import BaseRepository


class MarketingDetailRepository(BaseRepository):
    TABLE_NAME = 'marketing_detail'
    UNIQUE_KEY = 'detailId'
    SYSTEM_PREFIX = 'wdt'




