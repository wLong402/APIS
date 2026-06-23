# -*- coding: utf-8 -*-

from common.base_repository import BaseRepository


class MarketingShareResultRepository(BaseRepository):
    TABLE_NAME = 'marketing_share_result'
    UNIQUE_KEY = 'rowKey'
    SYSTEM_PREFIX = 'wdt'

    # 抖音全域直播间等稀疏字段：首批数据可能全是千川赠款，仍需预留列
    RESERVED_COLUMNS = {
        'roomId': 'NVARCHAR(64)',
        'authorId': 'NVARCHAR(64)',
        'liveSessionId': 'NVARCHAR(64)',
        'orderTools': 'NVARCHAR(64)',
        'advertiserId': 'NVARCHAR(64)',
    }
