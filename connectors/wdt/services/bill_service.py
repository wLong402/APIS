# -*- coding: utf-8 -*-
"""
账单标准拉取服务

从慧经营拉取账单数据
"""

from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import BillStandardRepository
from ..sdk.api import BillStandardQueryAPI


class BillStandardPullService(BasePullService):
    """
    账单标准拉取服务
    
    从慧经营拉取账单数据并保存到数据库
    
    配置项（config.yaml 中 wdt 节点下）:
        hjy_app_id: 慧经营应用ID
        hjy_sid: 卖家账号
        hjy_secret: 慧经营签名密钥
    """
    
    SERVICE_NAME = 'bill_standard'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'bill_standard_query'
    
    def __init__(self, client: WdtClient = None, repository: BillStandardRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or BillStandardRepository()
        super().__init__(self.client, self.repo)
        
    @property
    def bill_api(self) -> BillStandardQueryAPI:
        """获取账单API"""
        return self.client.bill_standard_api
    
    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        """
        从 API 获取账单数据
        
        Args:
            start_time: 开始日期（格式：YYYY-MM-DD）
            end_time: 结束日期（格式：YYYY-MM-DD）
            **kwargs: 其他参数
                - shop_no: 店铺编码列表
                - debug: 调试模式
                - max_workers: 并行线程数
                
        Returns:
            账单数据列表
        """
        # 提取日期部分
        start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
        end_date = end_time.split(' ')[0] if ' ' in end_time else end_time
        
        shop_no = kwargs.get('shop_no')
        if isinstance(shop_no, str):
            shop_no = [shop_no]
        
        # 如果是单日查询
        if start_date == end_date:
            return self.bill_api.query_all(
                business_time=start_date,
                shop_no=shop_no,
                debug=kwargs.get('debug', False)
            )
        
        # 日期范围查询
        return self.bill_api.query_date_range(
            start_date=start_date,
            end_date=end_date,
            shop_no=shop_no,
            debug=kwargs.get('debug', False),
            max_workers=kwargs.get('max_workers', 5)
        )

