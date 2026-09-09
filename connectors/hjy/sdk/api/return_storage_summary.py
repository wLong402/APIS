# -*- coding: utf-8 -*-
"""
退货入库汇总 wdt.hjy.recon.return.storage.summary.query
文档: https://open.wangdian.cn/hjy/open/apidoc/doc?path=wdt.hjy.recon.return.storage.summary.query
"""

from typing import Dict, Optional, List

from ..base import HjyQimenAPI, format_array_param, emit_debug, summarize_debug_dict


class ReconReturnStorageSummaryQueryAPI(HjyQimenAPI):
    METHOD = 'wdt.hjy.recon.return.storage.summary.query'
    LOGGER_NAME = 'connector.hjy.recon_return_storage_summary'

    def query(
        self,
        business_date: str,
        shop_no: Optional[List[str]] = None,
        warehouse_no: Optional[List[str]] = None,
        spec_no: Optional[List[str]] = None,
        summary_no: Optional[List[str]] = None,
        refund_stage: Optional[str] = None,
        salesman_name: Optional[str] = None,
        author_name: Optional[str] = None,
        goods_batch_no: Optional[str] = None,
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
                'refund_stage': refund_stage,
                'salesman_name': salesman_name,
                'author_name': author_name,
                'goods_batch_no': goods_batch_no,
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
        ):
            v = format_array_param(values)
            if v:
                sign_params[key] = v
        if refund_stage:
            sign_params['refundStage'] = refund_stage
        if salesman_name:
            sign_params['salesmanName'] = salesman_name
        if author_name:
            sign_params['authorName'] = author_name
        if goods_batch_no:
            sign_params['goodsBatchNo'] = goods_batch_no
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
        refund_stage: Optional[str] = None,
        salesman_name: Optional[str] = None,
        author_name: Optional[str] = None,
        goods_batch_no: Optional[str] = None,
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
            ):
                v = format_array_param(values)
                if v:
                    sign_params[key] = v
            if refund_stage:
                sign_params['refundStage'] = refund_stage
            if salesman_name:
                sign_params['salesmanName'] = salesman_name
            if author_name:
                sign_params['authorName'] = author_name
            if goods_batch_no:
                sign_params['goodsBatchNo'] = goods_batch_no
            if next_id and next_id != 'false':
                sign_params['nextRequestId'] = next_id
            return sign_params

        return self._paginate(build, debug=debug)
