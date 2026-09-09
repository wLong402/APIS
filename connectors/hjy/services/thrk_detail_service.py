# -*- coding: utf-8 -*-
"""退货入库明细拉取：wdt.hjy.recon.thrk.detail.query（startBusinessTime/endBusinessTime，跨度不超过一周）"""

from typing import List, Dict, Optional

from common.base_service import BasePullService
from ..client import get_hjy_client
from ..repositories import ReconThrkDetailRepository
from ..sdk.api import ReconThrkDetailQueryAPI


def _split_csv(val) -> Optional[List[str]]:
    if not val or not str(val).strip():
        return None
    return [x.strip() for x in str(val).split(',') if x.strip()]


class ReconThrkDetailPullService(BasePullService):
    SERVICE_NAME = 'recon_thrk_detail'
    SYSTEM_NAME = 'hjy'
    API_NAME = 'recon_thrk_detail_query'
    # 文档：退货入库日期限制不能超过一周
    TIME_SPAN_MINUTES = 7 * 24 * 60

    def __init__(self, client=None, repository: ReconThrkDetailRepository = None):
        self.client = client or get_hjy_client()
        self.repo = repository or ReconThrkDetailRepository()
        super().__init__(self.client, self.repo)

    @property
    def thrk_detail_api(self) -> ReconThrkDetailQueryAPI:
        return self.client.recon_thrk_detail_api

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        # 显式业务时间优先，否则用拉取窗口映射为 startBusinessTime/endBusinessTime
        start_bt = kwargs.get('start_business_time') or start_time
        end_bt = kwargs.get('end_business_time') or end_time
        if not start_bt or not end_bt:
            raise ValueError('recon_thrk_detail 必须提供 startBusinessTime / endBusinessTime（可用 --start/--end）')

        shop_list = None
        if kwargs.get('shop_nos'):
            shop_list = _split_csv(kwargs['shop_nos'])
        elif kwargs.get('shop_no'):
            shop_list = [str(kwargs['shop_no']).strip()]

        wh = kwargs.get('warehouse_nos') or kwargs.get('warehouse_no')
        return self.thrk_detail_api.query_all(
            start_business_time=start_bt,
            end_business_time=end_bt,
            shop_no=shop_list,
            warehouse_no=_split_csv(wh) if wh else None,
            spec_no=_split_csv(kwargs.get('spec_no')),
            summary_no=_split_csv(kwargs.get('summary_no')),
            oms_order_no=_split_csv(
                kwargs.get('oms_order_nos') or kwargs.get('oms_order_no') or kwargs.get('erp_order_nos')
            ),
            oms_stockin_no=_split_csv(kwargs.get('oms_stockin_nos') or kwargs.get('stockin_no')),
            oms_refund_no=_split_csv(kwargs.get('oms_refund_nos') or kwargs.get('refund_no')),
            plat_order_no=_split_csv(kwargs.get('plat_order_nos') or kwargs.get('plat_order_no')),
            province_names=_split_csv(kwargs.get('province_names')),
            city_names=_split_csv(kwargs.get('city_names')),
            district_names=_split_csv(kwargs.get('district_names')),
            refund_stage=kwargs.get('refund_stage') or kwargs.get('refund_type'),
            salesman_name=kwargs.get('salesman_name'),
            author_name=kwargs.get('author_name'),
            goods_batch_no=kwargs.get('goods_batch_no'),
            debug=kwargs.get('debug', False),
        )
