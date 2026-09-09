# -*- coding: utf-8 -*-
"""
退货入库明细 wdt.hjy.recon.thrk.detail.query
文档: https://open.wangdian.cn/hjy/open/apidoc/doc?path=wdt.hjy.recon.thrk.detail.query

与退货入库汇总（wdt.hjy.recon.return.storage.summary.query）是不同接口：
本接口返回明细行，并区分售中/售后（refundStage）。
"""

from typing import Dict, Optional, List

from ..base import HjyQimenAPI, format_array_param, emit_debug, summarize_debug_dict

_ARRAY_FIELDS = (
    ('shopNo', 'shop_no'),
    ('warehouseNo', 'warehouse_no'),
    ('specNo', 'spec_no'),
    ('summaryNo', 'summary_no'),
    ('omsOrderNo', 'oms_order_no'),
    ('omsStockinNo', 'oms_stockin_no'),
    ('omsRefundNo', 'oms_refund_no'),
    ('platOrderNo', 'plat_order_no'),
    ('provinceNames', 'province_names'),
    ('cityNames', 'city_names'),
    ('districtNames', 'district_names'),
)

_SCALAR_FIELDS = (
    ('refundStage', 'refund_stage'),
    ('salesmanName', 'salesman_name'),
    ('authorName', 'author_name'),
    ('goodsBatchNo', 'goods_batch_no'),
)


class ReconThrkDetailQueryAPI(HjyQimenAPI):
    METHOD = 'wdt.hjy.recon.thrk.detail.query'
    LOGGER_NAME = 'connector.hjy.recon_thrk_detail'

    def _build_sign_params(
        self,
        start_business_time: str,
        end_business_time: str,
        next_request_id: Optional[str] = None,
        **filters,
    ) -> Dict:
        sign_params = {
            'appId': self.hjy_app_id,
            'sid': self.hjy_sid,
            'startBusinessTime': start_business_time,
            'endBusinessTime': end_business_time,
        }
        for api_key, arg_name in _ARRAY_FIELDS:
            v = format_array_param(filters.get(arg_name))
            if v:
                sign_params[api_key] = v
        for api_key, arg_name in _SCALAR_FIELDS:
            v = filters.get(arg_name)
            if v:
                sign_params[api_key] = str(v)
        if next_request_id and next_request_id != 'false':
            sign_params['nextRequestId'] = next_request_id
        return sign_params

    def query(
        self,
        start_business_time: str,
        end_business_time: str,
        shop_no: Optional[List[str]] = None,
        warehouse_no: Optional[List[str]] = None,
        spec_no: Optional[List[str]] = None,
        summary_no: Optional[List[str]] = None,
        oms_order_no: Optional[List[str]] = None,
        oms_stockin_no: Optional[List[str]] = None,
        oms_refund_no: Optional[List[str]] = None,
        plat_order_no: Optional[List[str]] = None,
        province_names: Optional[List[str]] = None,
        city_names: Optional[List[str]] = None,
        district_names: Optional[List[str]] = None,
        refund_stage: Optional[str] = None,
        salesman_name: Optional[str] = None,
        author_name: Optional[str] = None,
        goods_batch_no: Optional[str] = None,
        next_request_id: Optional[str] = None,
        debug: bool = False,
    ) -> Dict:
        """查询退货入库明细（单页）。startBusinessTime/endBusinessTime 跨度不能超过一周。"""
        filters = {
            'shop_no': shop_no,
            'warehouse_no': warehouse_no,
            'spec_no': spec_no,
            'summary_no': summary_no,
            'oms_order_no': oms_order_no,
            'oms_stockin_no': oms_stockin_no,
            'oms_refund_no': oms_refund_no,
            'plat_order_no': plat_order_no,
            'province_names': province_names,
            'city_names': city_names,
            'district_names': district_names,
            'refund_stage': refund_stage,
            'salesman_name': salesman_name,
            'author_name': author_name,
            'goods_batch_no': goods_batch_no,
        }
        if debug:
            _inputs = dict(filters)
            _inputs.update({
                'start_business_time': start_business_time,
                'end_business_time': end_business_time,
                'next_request_id': next_request_id,
            })
            emit_debug(
                self.LOGGER_NAME,
                f"      [REQUEST DEBUG] query() 入参: {summarize_debug_dict(_inputs)}",
            )

        sign_params = self._build_sign_params(
            start_business_time, end_business_time, next_request_id, **filters
        )
        return self._call(sign_params, debug=debug)

    def query_all(
        self,
        start_business_time: str,
        end_business_time: str,
        shop_no: Optional[List[str]] = None,
        warehouse_no: Optional[List[str]] = None,
        spec_no: Optional[List[str]] = None,
        summary_no: Optional[List[str]] = None,
        oms_order_no: Optional[List[str]] = None,
        oms_stockin_no: Optional[List[str]] = None,
        oms_refund_no: Optional[List[str]] = None,
        plat_order_no: Optional[List[str]] = None,
        province_names: Optional[List[str]] = None,
        city_names: Optional[List[str]] = None,
        district_names: Optional[List[str]] = None,
        refund_stage: Optional[str] = None,
        salesman_name: Optional[str] = None,
        author_name: Optional[str] = None,
        goods_batch_no: Optional[str] = None,
        debug: bool = False,
    ) -> List[Dict]:
        filters = {
            'shop_no': shop_no,
            'warehouse_no': warehouse_no,
            'spec_no': spec_no,
            'summary_no': summary_no,
            'oms_order_no': oms_order_no,
            'oms_stockin_no': oms_stockin_no,
            'oms_refund_no': oms_refund_no,
            'plat_order_no': plat_order_no,
            'province_names': province_names,
            'city_names': city_names,
            'district_names': district_names,
            'refund_stage': refund_stage,
            'salesman_name': salesman_name,
            'author_name': author_name,
            'goods_batch_no': goods_batch_no,
        }

        def build(next_id: Optional[str]) -> Dict:
            return self._build_sign_params(
                start_business_time, end_business_time, next_id, **filters
            )

        return self._paginate(build, debug=debug)
