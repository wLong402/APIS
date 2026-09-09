# -*- coding: utf-8 -*-

from typing import List, Dict

from core.logger import debug_print
from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import GoodsRepository
from ..sdk.api import QueryGoodsWithSpecAPI


class GoodsQueryWithSpecPullService(BasePullService):
    """货品档案拉取（OpenAPI goods.Goods.queryWithSpec）"""

    SERVICE_NAME = 'goods_query_with_spec'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'query_goods_with_spec'
    # 文档：start_time / end_time 最大跨度 30 天
    TIME_SPAN_MINUTES = 30 * 24 * 60

    def __init__(self, client: WdtClient = None, repository: GoodsRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or GoodsRepository()
        super().__init__(self.client, self.repo)

    @property
    def goods_api(self) -> QueryGoodsWithSpecAPI:
        return self.client.goods_query_with_spec_api

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        debug = kwargs.get('debug', False)
        page_size = kwargs.get('page_size', 200)

        hide_deleted = kwargs.get('hide_deleted')
        if hide_deleted is None or hide_deleted == '':
            hide_deleted = 1
        else:
            hide_deleted = int(hide_deleted)

        if debug:
            debug_print(f"    [DEBUG] 调用 API: {self.goods_api.METHOD}")

        return self.goods_api.query_all(
            start_time=start_time,
            end_time=end_time,
            spec_no=kwargs.get('spec_no'),
            goods_no=kwargs.get('goods_no'),
            brand_name=kwargs.get('brand_name'),
            class_name=kwargs.get('class_name'),
            barcode=kwargs.get('barcode'),
            hide_deleted=hide_deleted,
            page_size=page_size,
            debug=debug,
        )
