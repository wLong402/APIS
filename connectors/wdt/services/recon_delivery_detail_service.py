# -*- coding: utf-8 -*-

import time
from typing import List, Dict, Optional

from common.base_service import BasePullService, PullResult
from core.logger import debug_print
from ..client import WdtClient, get_wdt_client
from ..repositories import ReconDeliveryDetailRepository
from ..sdk.api import ReconDeliveryDetailQueryAPI


def _split_csv(val) -> Optional[List[str]]:
    if not val or not str(val).strip():
        return None
    return [x.strip() for x in str(val).split(',') if x.strip()]


class ReconDeliveryDetailPullService(BasePullService):
    SERVICE_NAME = 'recon_delivery_detail'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'recon_delivery_detail_query'

    def __init__(self, client: WdtClient = None, repository: ReconDeliveryDetailRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or ReconDeliveryDetailRepository()
        super().__init__(self.client, self.repo)

    @property
    def recon_delivery_detail_api(self) -> ReconDeliveryDetailQueryAPI:
        return self.client.recon_delivery_detail_api

    @staticmethod
    def _fmt_count(v: int) -> str:
        return f'{v:,}'

    def _build_query_params(self, start_time: Optional[str], end_time: Optional[str], **kwargs) -> Dict:
        start_date = None
        end_date = None
        if start_time:
            start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
        if end_time:
            end_date = end_time.split(' ')[0] if ' ' in end_time else end_time

        shop_list = None
        if kwargs.get('shop_nos'):
            shop_list = [x.strip() for x in kwargs['shop_nos'].split(',') if x.strip()]
        elif kwargs.get('shop_no'):
            shop_list = [kwargs['shop_no'].strip()]

        wh = kwargs.get('warehouse_nos') or kwargs.get('warehouse_no')
        warehouse_list = _split_csv(wh) if wh else None

        return {
            'start_date': start_date,
            'end_date': end_date,
            'period_mark': kwargs.get('period_mark'),
            'shop_no': shop_list,
            'warehouse_no': warehouse_list,
            'spec_no': _split_csv(kwargs.get('spec_no')),
            'summary_no': _split_csv(kwargs.get('summary_no')),
            'reco_status': _split_csv(kwargs.get('reco_status')),
            'plat_order_no': _split_csv(kwargs.get('plat_order_nos')),
            'salesman_name': kwargs.get('salesman_name'),
            'start_business_time': kwargs.get('start_business_time'),
            'end_business_time': kwargs.get('end_business_time'),
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

        try:
            self.before_pull(start_time, end_time, **kwargs)

            while True:
                page_no += 1
                if debug:
                    debug_print(f"    [DEBUG] 查询第 {page_no} 页...")
                resp = self.recon_delivery_detail_api.query(
                    period_mark=query_params.get('period_mark'),
                    start_date=query_params.get('start_date'),
                    end_date=query_params.get('end_date'),
                    shop_no=query_params.get('shop_no'),
                    warehouse_no=query_params.get('warehouse_no'),
                    spec_no=query_params.get('spec_no'),
                    summary_no=query_params.get('summary_no'),
                    reco_status=query_params.get('reco_status'),
                    plat_order_no=query_params.get('plat_order_no'),
                    salesman_name=query_params.get('salesman_name'),
                    start_business_time=query_params.get('start_business_time'),
                    end_business_time=query_params.get('end_business_time'),
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
                        if debug:
                            debug_print(
                                f"    [FLUSH] 触发落库 批量={self._fmt_count(to_save)} "
                                f"成功={self._fmt_count(saved_now)} "
                                f"累计落库={self._fmt_count(result.saved)} "
                                f"累计获取={self._fmt_count(result.fetched)}"
                            )
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
                if debug:
                    debug_print(
                        f"    [FLUSH] 收尾落库 批量={self._fmt_count(to_save)} "
                        f"成功={self._fmt_count(saved_now)} "
                        f"累计落库={self._fmt_count(result.saved)} "
                        f"累计获取={self._fmt_count(result.fetched)}"
                    )

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

        return self.recon_delivery_detail_api.query_all(
            start_date=query_params.get('start_date'),
            end_date=query_params.get('end_date'),
            period_mark=query_params.get('period_mark'),
            shop_no=query_params.get('shop_no'),
            warehouse_no=query_params.get('warehouse_no'),
            spec_no=query_params.get('spec_no'),
            summary_no=query_params.get('summary_no'),
            reco_status=query_params.get('reco_status'),
            plat_order_no=query_params.get('plat_order_no'),
            salesman_name=query_params.get('salesman_name'),
            start_business_time=query_params.get('start_business_time'),
            end_business_time=query_params.get('end_business_time'),
            debug=query_params.get('debug', False),
        )
