# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ReconDztkSummaryRepository(BaseRepository):
    TABLE_NAME = 'recon_dztk_summary'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
