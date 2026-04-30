# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ShtReconDetailRepository(BaseRepository):
    TABLE_NAME = 'sht_recon_detail'
    UNIQUE_KEY = 'detailId'
    SYSTEM_PREFIX = 'wdt'
