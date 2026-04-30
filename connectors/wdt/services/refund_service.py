# -*- coding: utf-8 -*-
"""
退款单拉取服务
"""

from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import RefundRepository
from ..sdk.api import RefundTimeType


class RefundPullService(BasePullService):
    """
    退款单拉取服务
    
    从旺店通拉取退款单数据并保存到数据库
    """
    
    SERVICE_NAME = 'refund'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'raw_refund'
    
    def __init__(self, client: WdtClient = None, repository: RefundRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or RefundRepository()
        super().__init__(self.client, self.repo)
    
    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        """从 API 获取退款单数据"""
        return self.client.raw_refund_api.search_all(
            start_time=start_time,
            end_time=end_time,
            time_type=kwargs.get('time_type', RefundTimeType.MODIFIED_TIME),
            shop_no=kwargs.get('shop_no'),
            page_size=kwargs.get('page_size', 200),
            debug=kwargs.get('debug', False),
            max_workers=kwargs.get('max_workers', 10)
        )
