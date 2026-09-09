# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ReconOrderConfirmSummaryRepository(BaseRepository):
    TABLE_NAME = 'recon_order_confirm_summary'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
