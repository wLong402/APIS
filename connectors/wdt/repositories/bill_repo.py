# -*- coding: utf-8 -*-
"""
账单标准数据仓库

存储慧经营账单数据
唯一键：detailId（明细ID）
"""

from common.base_repository import BaseRepository


class BillStandardRepository(BaseRepository):
    """账单标准数据仓库"""
    
    TABLE_NAME = 'bill_standard'
    UNIQUE_KEY = 'detailId'
    SYSTEM_PREFIX = 'wdt'

