# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class ReconThrkDetailRepository(BaseRepository):
    """退货入库明细；UK=detailId"""

    TABLE_NAME = 'recon_thrk_detail'
    UNIQUE_KEY = 'detailId'
    SYSTEM_PREFIX = 'wdt'
