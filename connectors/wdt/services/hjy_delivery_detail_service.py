# -*- coding: utf-8 -*-
"""
慧经营发货明细拉取

API: wdt.hjy.recon.delivery.detail.query
文档要求 startBusinessTime / endBusinessTime，最大跨度 7 天。
"""

import time
from typing import List, Dict, Optional

from common.base_service import BasePullService, PullResult
from core.logger import debug_print
from ..client import WdtClient, get_wdt_client
from ..repositories import HjyDeliveryDetailRepository
from ..sdk.api import HjyDeliveryDetailQueryAPI


def _split_csv(val) -> Optional[List[str]]:
    if not val or not str(val).strip():
        return None
    return [x.strip() for x in str(val).split(',') if x.strip()]


class HjyDeliveryDetailPullService(BasePullService):
    SERVICE_NAME = 'hjy_delivery_detail'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'hjy_delivery_detail_query'
    # 文档：发货日期限制不能超过一周
    TIME_SPAN_MINUTES = 7 * 24 * 60

    def __init__(self, client: WdtClient = None, repository: HjyDeliveryDetailRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or HjyDeliveryDetailRepository()
        super().__init__(self.client, self.repo)

    @property
    def hjy_delivery_detail_api(self) -> HjyDeliveryDetailQueryAPI:
        return self.client.hjy_delivery_detail_api

    @staticmethod
    def _fmt_count(v: int) -> str:
        return f'{v:,}'

    def _build_query_params(self, start_time: Optional[str], end_time: Optional[str], **kwargs) -> Dict:
        # 显式业务时间优先，否则用拉取窗口映射为 startBusinessTime/endBusinessTime
        start_bt = kwargs.get('start_business_time') or start_time
        end_bt = kwargs.get('end_business_time') or end_time

        shop_list = None
        if kwargs.get('shop_nos'):
            shop_list = _split_csv(kwargs['shop_nos'])
        elif kwargs.get('shop_no'):
            shop_list = [str(kwargs['shop_no']).strip()]

        wh = kwargs.get('warehouse_nos') or kwargs.get('warehouse_no')
        return {
            'start_business_time': start_bt,
            'end_business_time': end_bt,
            'shop_no': shop_list,
            'warehouse_no': _split_csv(wh) if wh else None,
            'spec_no': _split_csv(kwargs.get('spec_no')),
            'summary_no': _split_csv(kwargs.get('summary_no')),
            'oms_stockout_no': _split_csv(kwargs.get('oms_stockout_nos') or kwargs.get('oms_stockout_no')),
            'province_names': _split_csv(kwargs.get('province_names')),
            'city_names': _split_csv(kwargs.get('city_names')),
            'district_names': _split_csv(kwargs.get('district_names')),
            'plat_order_no': _split_csv(kwargs.get('plat_order_nos') or kwargs.get('plat_order_no')),
            'author_name': kwargs.get('author_name'),
            'salesman_name': kwargs.get('salesman_name'),
            'oms_order_no': _split_csv(kwargs.get('oms_order_nos') or kwargs.get('oms_order_no') or kwargs.get('erp_order_nos')),
            'debug': kwargs.get('debug', False),
        }

    def pull(self, start_time: str, end_time: str, **kwargs) -> PullResult:
        start_ts = time.time()
        result = PullResult()
        flush_size = 100000
        buffer: List[Dict] = []
        query_params = self._build_query_params(start_time, end_time, **kwargs)
        debug = bool(query_params.get('debug'))
        next_request_id = None
        page_no = 0

        start_bt = query_params.get('start_business_time')
        end_bt = query_params.get('end_business_time')
        if not start_bt or not end_bt:
            result.errors = 1
            result.details['error'] = 'hjy_delivery_detail 必须提供 startBusinessTime / endBusinessTime（可用 --start/--end）'
            result.duration = time.time() - start_ts
            return result

        try:
            self.before_pull(start_time, end_time, **kwargs)

            while True:
                page_no += 1
                if debug:
                    debug_print(f"    [DEBUG] 查询第 {page_no} 页...")
                resp = self.hjy_delivery_detail_api.query(
                    start_business_time=start_bt,
                    end_business_time=end_bt,
                    shop_no=query_params.get('shop_no'),
                    warehouse_no=query_params.get('warehouse_no'),
                    spec_no=query_params.get('spec_no'),
                    summary_no=query_params.get('summary_no'),
                    oms_stockout_no=query_params.get('oms_stockout_no'),
                    province_names=query_params.get('province_names'),
                    city_names=query_params.get('city_names'),
                    district_names=query_params.get('district_names'),
                    plat_order_no=query_params.get('plat_order_no'),
                    author_name=query_params.get('author_name'),
                    salesman_name=query_params.get('salesman_name'),
                    oms_order_no=query_params.get('oms_order_no'),
                    next_request_id=next_request_id,
                    debug=debug,
                )
                if str(resp.get('resultCode')) != '200':
                    raise RuntimeError(resp.get('message') or '接口返回失败')

                data_list = resp.get('data', []) or []
                page_count = len(data_list)
                if data_list:
                    result.fetched += len(data_list)
                    buffer.extend(data_list)
                    if debug:
                        debug_print(
                            f"    [PROGRESS] 页={page_no} 本页获取={self._fmt_count(page_count)} "
                            f"累计获取={self._fmt_count(result.fetched)} "
                            f"累计落库={self._fmt_count(result.saved)} "
                            f"待落库={self._fmt_count(len(buffer))}"
                        )
                    if len(buffer) >= flush_size:
                        to_save = len(buffer)
                        saved_now = self.repo.save_batch(
                            buffer,
                            debug=debug,
                            progress_label=f"{self.SYSTEM_NAME}.{self.SERVICE_NAME}",
                        ) if self.repo else to_save
                        result.saved += saved_now
                        buffer = []

                next_request_id = resp.get('nextRequestId')
                if not next_request_id or next_request_id == 'false':
                    break
                time.sleep(0.1)

            if buffer:
                to_save = len(buffer)
                saved_now = self.repo.save_batch(
                    buffer,
                    debug=debug,
                    progress_label=f"{self.SYSTEM_NAME}.{self.SERVICE_NAME}",
                ) if self.repo else to_save
                result.saved += saved_now

            result.errors = result.fetched - result.saved
            if debug:
                debug_print(
                    f"    [PROGRESS] 完成 总页数={page_no} "
                    f"总获取={self._fmt_count(result.fetched)} "
                    f"总落库={self._fmt_count(result.saved)} "
                    f"差异={self._fmt_count(result.errors)}"
                )
            if result.errors > 0:
                self._on_data_mismatch(result, start_time, end_time)
            self.after_pull(result, start_time, end_time, **kwargs)
        except Exception as e:
            self.on_error(e, start_time, end_time, **kwargs)
            result.errors = 1
            result.details['error'] = str(e)

        result.duration = time.time() - start_ts
        return result

    def _fetch_data(self, start_time: Optional[str], end_time: Optional[str], **kwargs) -> List[Dict]:
        query_params = self._build_query_params(start_time, end_time, **kwargs)
        start_bt = query_params.get('start_business_time')
        end_bt = query_params.get('end_business_time')
        if not start_bt or not end_bt:
            raise ValueError('hjy_delivery_detail 必须提供 startBusinessTime / endBusinessTime')

        return self.hjy_delivery_detail_api.query_all(
            start_business_time=start_bt,
            end_business_time=end_bt,
            shop_no=query_params.get('shop_no'),
            warehouse_no=query_params.get('warehouse_no'),
            spec_no=query_params.get('spec_no'),
            summary_no=query_params.get('summary_no'),
            oms_stockout_no=query_params.get('oms_stockout_no'),
            province_names=query_params.get('province_names'),
            city_names=query_params.get('city_names'),
            district_names=query_params.get('district_names'),
            plat_order_no=query_params.get('plat_order_no'),
            author_name=query_params.get('author_name'),
            salesman_name=query_params.get('salesman_name'),
            oms_order_no=query_params.get('oms_order_no'),
            debug=query_params.get('debug', False),
        )
