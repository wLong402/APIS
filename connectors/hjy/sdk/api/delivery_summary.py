# -*- coding: utf-8 -*-
"""
发货汇总 wdt.hjy.recon.delivery.summary.query
文档: https://open.wangdian.cn/hjy/open/apidoc/doc?path=wdt.hjy.recon.delivery.summary.query
"""

from typing import Dict, Optional, List

from ..base import HjyQimenAPI, format_array_param, emit_debug, summarize_debug_dict


class ReconDeliverySummaryQueryAPI(HjyQimenAPI):
    METHOD = 'wdt.hjy.recon.delivery.summary.query'
    LOGGER_NAME = 'connector.hjy.recon_delivery_summary'

    def query(
        self,
        business_date: str,
        shop_no: Optional[List[str]] = None,
        warehouse_no: Optional[List[str]] = None,
        spec_no: Optional[List[str]] = None,
        summary_no: Optional[List[str]] = None,
        author_name: Optional[str] = None,
        salesman_name: Optional[str] = None,
        province_names: Optional[List[str]] = None,
        city_names: Optional[List[str]] = None,
        district_names: Optional[List[str]] = None,
        next_request_id: Optional[str] = None,
        debug: bool = False,
    ) -> Dict:
        if debug:
            _inputs = {
                'business_date': business_date,
                'shop_no': shop_no,
                'warehouse_no': warehouse_no,
                'spec_no': spec_no,
                'summary_no': summary_no,
                'author_name': author_name,
                'salesman_name': salesman_name,
                'province_names': province_names,
                'city_names': city_names,
                'district_names': district_names,
                'next_request_id': next_request_id,
            }
            emit_debug(
                self.LOGGER_NAME,
                f"      [REQUEST DEBUG] query() 入参: {summarize_debug_dict(_inputs)}",
            )

        sign_params = {
            'appId': self.hjy_app_id,
            'sid': self.hjy_sid,
            'businessDate': business_date,
        }
        for key, values in (
            ('shopNo', shop_no),
            ('warehouseNo', warehouse_no),
            ('specNo', spec_no),
            ('summaryNo', summary_no),
            ('provinceNames', province_names),
            ('cityNames', city_names),
            ('districtNames', district_names),
        ):
            v = format_array_param(values)
            if v:
                sign_params[key] = v
        if author_name:
            sign_params['authorName'] = author_name
        if salesman_name:
            sign_params['salesmanName'] = salesman_name
        if next_request_id and next_request_id != 'false':
            sign_params['nextRequestId'] = next_request_id

        return self._call(sign_params, debug=debug)

    def query_all(
        self,
        business_date: str,
        shop_no: Optional[List[str]] = None,
        warehouse_no: Optional[List[str]] = None,
        spec_no: Optional[List[str]] = None,
        summary_no: Optional[List[str]] = None,
        author_name: Optional[str] = None,
        salesman_name: Optional[str] = None,
        province_names: Optional[List[str]] = None,
        city_names: Optional[List[str]] = None,
        district_names: Optional[List[str]] = None,
        debug: bool = False,
    ) -> List[Dict]:
        def build(next_id: Optional[str]) -> Dict:
            sign_params = {
                'appId': self.hjy_app_id,
                'sid': self.hjy_sid,
                'businessDate': business_date,
            }
            for key, values in (
                ('shopNo', shop_no),
                ('warehouseNo', warehouse_no),
                ('specNo', spec_no),
                ('summaryNo', summary_no),
                ('provinceNames', province_names),
                ('cityNames', city_names),
                ('districtNames', district_names),
            ):
                v = format_array_param(values)
                if v:
                    sign_params[key] = v
            if author_name:
                sign_params['authorName'] = author_name
            if salesman_name:
                sign_params['salesmanName'] = salesman_name
            if next_id and next_id != 'false':
                sign_params['nextRequestId'] = next_id
            return sign_params

        return self._paginate(build, debug=debug)
