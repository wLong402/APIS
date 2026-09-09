# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ReconReturnStorageSummaryRepository(BaseRepository):
    """退货入库汇总；无业务主键，使用 rowKey。"""

    TABLE_NAME = 'recon_return_storage_summary'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'
