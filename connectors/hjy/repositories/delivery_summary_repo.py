# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ReconDeliverySummaryRepository(BaseRepository):
    """发货汇总；无业务主键，使用 rowKey。"""

    TABLE_NAME = 'recon_delivery_summary'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
