# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class GoodsSpecRepository(BaseRepository):
    """货品单品规格表（spec_list）"""

    TABLE_NAME = 'goods_spec'
    UNIQUE_KEY = 'spec_id'
    SYSTEM_PREFIX = 'wdt'
