#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
import time
from typing import Dict, Optional, List
from urllib.parse import urlencode

import requests

from ..client import QimenClient
from ..config import WdtConfig
from ..sign import WdtSignUtil


def _get_debug_print():
    try:
        from utils.logger import debug_print
        return debug_print
    except ImportError:
        return lambda msg, end='\n', flush=False: print(f"    {msg}", end=end, flush=flush)


def _emit_debug(msg: str) -> None:
    _get_debug_print()(msg)
    try:
        from core.logger import get_logger
        get_logger('connector.wdt.sht_recon_detail').info(msg)
    except Exception:
        pass


class ShtReconDetailQueryAPI:
    METHOD = 'wdt.hjy.recon.shtrecondetail.query'
    PAGE_SIZE = 200

    def __init__(
        self,
        client: Optional[QimenClient] = None,
        config: Optional[WdtConfig] = None,
        hjy_app_id: str = '',
        hjy_sid: str = '',
        hjy_app_key: str = '',
        hjy_gateway_url: str = '',
    ):
        self.client = client or QimenClient(config)
        self.config = config or self.client.config
        self.hjy_app_id = hjy_app_id
        self.hjy_sid = hjy_sid
        self.hjy_app_key = hjy_app_key
        self.gateway_url = hjy_gateway_url or self.config.gateway_url

    def _generate_hjy_sign(self, params: Dict, app_key: str) -> str:
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        param_str = '&'.join(f"{k}:{v}" for k, v in sorted_params)
        param_str += app_key
        param_str = param_str.replace('"', '').replace(' ', '')
        return hashlib.md5(param_str.encode('utf-8')).hexdigest().lower()

    @staticmethod
    def _format_array_param(values: Optional[List[str]], mode: str = 'json') -> Optional[str]:
        if not values:
            return None
        cleaned = [str(v).strip() for v in values if str(v).strip()]
        if not cleaned:
            return None
        if mode == 'scalar':
            return cleaned[0]
        if mode == 'csv':
            return ','.join(cleaned)
        return json.dumps(cleaned, ensure_ascii=False)

    @staticmethod
    def _is_sign_failure(resp_data: Dict) -> bool:
        if not isinstance(resp_data, dict):
            return False
        code = str(resp_data.get('code', ''))
        sub_code = str(resp_data.get('sub_code', '')).lower()
        message = str(resp_data.get('message', '')).lower()
        return code in ('15', '25') or 'sign' in sub_code or 'invalid signature' in message

    def _request_once(self, api_params: Dict, sys_params: Dict, debug: bool = False) -> Dict:
        request_url = f"{self.gateway_url}?{urlencode({k: str(v) for k, v in sys_params.items()})}"
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    request_url,
                    data=api_params,
                    headers=headers,
                    timeout=self.config.timeout,
                )
                result = response.json()
                resp_data = result.get('response', result)

                if debug:
                    data_list = resp_data.get('data') if isinstance(resp_data, dict) else None
                    data_size = len(data_list) if isinstance(data_list, list) else 0
                    _emit_debug(f"      [REQUEST DEBUG] request_url: {request_url}")
                    _emit_debug(f"      [RESPONSE DEBUG] HTTP状态码: {response.status_code}")
                    _emit_debug(
                        "      [RESPONSE DEBUG] "
                        f"resultCode={resp_data.get('resultCode')}, "
                        f"message={resp_data.get('message', '')}, "
                        f"data_count={data_size}, "
                        f"nextRequestId={resp_data.get('nextRequestId')}"
                    )

                result_code = resp_data.get('resultCode')
                msg = resp_data.get('message', '')
                if result_code is None or '繁忙' in msg or 'busy' in msg.lower():
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue

                return resp_data
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return {'resultCode': 'error', 'message': str(e)}
            except json.JSONDecodeError:
                return {'resultCode': 'error', 'message': '响应不是有效的JSON格式'}

        return {'resultCode': 'error', 'message': '重试次数用尽'}

    def query(
        self,
        period_mark: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        refund_type: Optional[List[str]] = None,
        shop_no: Optional[List[str]] = None,
        warehouse_no: Optional[List[str]] = None,
        spec_no: Optional[List[str]] = None,
        summary_no: Optional[List[str]] = None,
        reco_status: Optional[List[str]] = None,
        plat_order_no: Optional[List[str]] = None,
        salesman_name: Optional[str] = None,
        sys_order_no: Optional[List[str]] = None,
        next_request_id: Optional[str] = None,
        debug: bool = False,
    ) -> Dict:
        if debug:
            _inputs = {
                'period_mark': period_mark,
                'start_date': start_date,
                'end_date': end_date,
                'refund_type': refund_type,
                'shop_no': shop_no,
                'warehouse_no': warehouse_no,
                'spec_no': spec_no,
                'summary_no': summary_no,
                'reco_status': reco_status,
                'plat_order_no': plat_order_no,
                'salesman_name': salesman_name,
                'sys_order_no': sys_order_no,
                'next_request_id': next_request_id,
            }
            _inputs = {k: v for k, v in _inputs.items() if v is not None}
            _emit_debug(f"      [REQUEST DEBUG] query() 入参: {json.dumps(_inputs, ensure_ascii=False, indent=2)}")

        sign_params = {
            'appId': self.hjy_app_id,
            'sid': self.hjy_sid,
        }

        if period_mark:
            sign_params['periodMark'] = period_mark
        if start_date:
            sign_params['startDate'] = start_date
        if end_date:
            sign_params['endDate'] = end_date
        has_array_filters = any([refund_type, shop_no, warehouse_no, spec_no, summary_no, reco_status, plat_order_no, sys_order_no])
        array_modes = ['json', 'scalar', 'csv'] if has_array_filters else ['json']
        last_resp = {'resultCode': 'error', 'message': '未获取到响应'}

        for mode in array_modes:
            sign_params = {
                'appId': self.hjy_app_id,
                'sid': self.hjy_sid,
            }
            if period_mark:
                sign_params['periodMark'] = period_mark
            if start_date:
                sign_params['startDate'] = start_date
            if end_date:
                sign_params['endDate'] = end_date
            v = self._format_array_param(refund_type, mode)
            if v:
                sign_params['refundType'] = v
            v = self._format_array_param(shop_no, mode)
            if v:
                sign_params['shopNo'] = v
            v = self._format_array_param(warehouse_no, mode)
            if v:
                sign_params['warehouseNo'] = v
            v = self._format_array_param(spec_no, mode)
            if v:
                sign_params['specNo'] = v
            v = self._format_array_param(summary_no, mode)
            if v:
                sign_params['summaryNo'] = v
            v = self._format_array_param(reco_status, mode)
            if v:
                sign_params['recoStatus'] = v
            v = self._format_array_param(plat_order_no, mode)
            if v:
                sign_params['platOrderNo'] = v
            if salesman_name:
                sign_params['salesmanName'] = salesman_name
            v = self._format_array_param(sys_order_no, mode)
            if v:
                sign_params['sysOrderNo'] = v
            if next_request_id and next_request_id != 'false':
                sign_params['nextRequestId'] = next_request_id

            hjy_sign = self._generate_hjy_sign(sign_params, self.hjy_app_key)
            api_params = dict(sign_params)
            api_params['hjySign'] = hjy_sign

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            sys_params = {
                'app_key': self.config.qimen_appkey,
                'v': '2.0',
                'format': 'json',
                'sign_method': 'md5',
                'method': self.METHOD,
                'timestamp': timestamp,
                'target_app_key': self.config.target_appkey,
                'session': '',
            }
            top_sign = WdtSignUtil.generate_top_sign(
                {**sys_params, **api_params},
                self.config.qimen_appsecret,
            )
            sys_params['sign'] = top_sign

            if debug:
                _emit_debug(f"      [API DEBUG] method: {self.METHOD}")
                _emit_debug(f"      [REQUEST DEBUG] sign_mode: {mode}")
                _emit_debug(f"      [REQUEST DEBUG] sign_params(签名字段): {json.dumps(sign_params, ensure_ascii=False, indent=2)}")
                _emit_debug(f"      [API DEBUG] post body(api_params): {json.dumps(api_params, ensure_ascii=False, indent=2)}")
                _emit_debug(f"      [REQUEST DEBUG] timestamp: {timestamp}")
                _emit_debug(f"      [REQUEST DEBUG] top_sign(奇门): {top_sign}")

            resp_data = self._request_once(api_params, sys_params, debug=debug)
            last_resp = resp_data
            if not self._is_sign_failure(resp_data):
                return resp_data
            if debug and mode != array_modes[-1]:
                _emit_debug("      [REQUEST DEBUG] 命中签名失败，自动切换下一种数组签名格式重试")

        return last_resp

    def query_all(
        self,
        period_mark: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        refund_type: Optional[List[str]] = None,
        shop_no: Optional[List[str]] = None,
        warehouse_no: Optional[List[str]] = None,
        spec_no: Optional[List[str]] = None,
        summary_no: Optional[List[str]] = None,
        reco_status: Optional[List[str]] = None,
        plat_order_no: Optional[List[str]] = None,
        salesman_name: Optional[str] = None,
        sys_order_no: Optional[List[str]] = None,
        debug: bool = False,
    ) -> List[Dict]:
        all_data = []
        next_request_id = None
        page_no = 1

        while True:
            if debug:
                _emit_debug(f"    [DEBUG] 查询第 {page_no} 页...")

            result = self.query(
                period_mark=period_mark,
                start_date=start_date,
                end_date=end_date,
                refund_type=refund_type,
                shop_no=shop_no,
                warehouse_no=warehouse_no,
                spec_no=spec_no,
                summary_no=summary_no,
                reco_status=reco_status,
                plat_order_no=plat_order_no,
                salesman_name=salesman_name,
                sys_order_no=sys_order_no,
                next_request_id=next_request_id,
                debug=debug,
            )

            if result.get('resultCode') != '200':
                if debug:
                    _emit_debug(f"    [DEBUG] 查询失败: {result.get('message')}")
                break

            data_list = result.get('data', [])
            if data_list:
                all_data.extend(data_list)

            next_request_id = result.get('nextRequestId')
            if not next_request_id or next_request_id == 'false':
                break

            page_no += 1
            time.sleep(0.1)

        if debug:
            _emit_debug(f"    [DEBUG] 查询完成，共 {len(all_data)} 条")
        return all_data
