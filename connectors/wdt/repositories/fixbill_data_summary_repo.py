# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class FixbillDataSummaryRepository(BaseRepository):
    TABLE_NAME = 'fixbill_data_summary'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
