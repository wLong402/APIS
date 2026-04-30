# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class BkShareDataRepository(BaseRepository):
    TABLE_NAME = 'bk_share_data'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
