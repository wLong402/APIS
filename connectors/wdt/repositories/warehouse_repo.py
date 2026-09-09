# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class WarehouseRepository(BaseRepository):
    TABLE_NAME = 'warehouse'
    UNIQUE_KEY = 'warehouse_id'
    SYSTEM_PREFIX = 'wdt'
