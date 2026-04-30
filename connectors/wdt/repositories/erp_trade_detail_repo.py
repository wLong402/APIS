# -*- coding: utf-8 -*-
"""
ERP订单明细数据仓库
"""

from common.base_repository import BaseRepository


class ErpTradeDetailRepository(BaseRepository):
    """ERP订单明细数据仓库"""
    
    TABLE_NAME = 'erp_trade_detail'
    UNIQUE_KEY = 'rec_id'
    SYSTEM_PREFIX = 'wdt'

