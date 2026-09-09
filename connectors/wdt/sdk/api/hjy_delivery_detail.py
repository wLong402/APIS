#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
慧经营发货明细

wdt.hjy.recon.delivery.detail.query
文档: https://open.wangdian.cn/hjy/open/apidoc/doc?path=wdt.hjy.recon.delivery.detail.query

与发货对账明细（wdt.hjy.recon.delivery.details.query）是不同接口。
"""

import hashlib
import json
import time
from typing import Dict, Optional, List
from urllib.parse import urlencode, urlparse

import requests

from ..client import QimenClient
from ..config import WdtConfig
from ..sign import WdtSignUtil
from .log_template import summarize_response


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
        get_logger('connector.wdt.hjy_delivery_detail').info(msg)
    except Exception:
        pass


def _summarize_debug_value(val, max_len: int = 96) -> str:
    if val is None:
        return 'None'
    if isinstance(val, list):
        return f'<{len(val)} items>'
    if isinstance(val, dict):
        return f'<{len(val)} keys>'
    s = str(val)
    if len(s) > max_len:
        return s[:max_len] + f'...<{len(s)} chars>'
    return s


def _summarize_debug_dict(d: Dict, max_len: int = 96) -> str:
    parts = []
    for k in sorted(d.keys()):
        v = d.get(k)
        if v is None:
            continue
        parts.append(f'{k}={_summarize_debug_value(v, max_len=max_len)}')
    return ', '.join(parts)


class HjyDeliveryDetailQueryAPI:
    """慧经营发货明细查询 API"""

    METHOD = 'wdt.hjy.recon.delivery.detail.query'
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
    def _format_array_param(values: Optional[List[str]]) -> Optional[str]:
        if not values:
            return None
        cleaned = [str(v).strip() for v in values if str(v).strip()]
        if not cleaned:
            return None
        return json.dumps(cleaned, ensure_ascii=False)

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
                er = result.get('error_response')
                if isinstance(er, dict):
                    msg = er.get('msg') or er.get('message') or 'error_response'
                    return {
                        'resultCode': str(er.get('code', 'error')),
                        'message': str(msg),
                        'sub_resultCode': str(er.get('sub_code', '')),
                        'data': [],
                    }
                resp_data = result.get('response', result)

                if debug:
                    host = urlparse(self.gateway_url).netloc or self.gateway_url
                    _emit_debug(f"      [REQUEST DEBUG] POST gateway={host}")
                    _emit_debug(
                        f"      [RESPONSE DEBUG] {summarize_response(resp_data, api_params=api_params, http_status=response.status_code)}"
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
        start_business_time: str,
        end_business_time: str,
        shop_no: Optional[List[str]] = None,
        warehouse_no: Optional[List[str]] = None,
        spec_no: Optional[List[str]] = None,
        summary_no: Optional[List[str]] = None,
        oms_stockout_no: Optional[List[str]] = None,
        province_names: Optional[List[str]] = None,
        city_names: Optional[List[str]] = None,
        district_names: Optional[List[str]] = None,
        plat_order_no: Optional[List[str]] = None,
        author_name: Optional[str] = None,
        salesman_name: Optional[str] = None,
        oms_order_no: Optional[List[str]] = None,
        next_request_id: Optional[str] = None,
        debug: bool = False,
    ) -> Dict:
        """
        查询发货明细（单页）

        Args:
            start_business_time / end_business_time: 发货日期，最大跨度 7 天
        """
        if debug:
            _inputs = {
                'start_business_time': start_business_time,
                'end_business_time': end_business_time,
                'shop_no': shop_no,
                'warehouse_no': warehouse_no,
                'spec_no': spec_no,
                'summary_no': summary_no,
                'oms_stockout_no': oms_stockout_no,
                'province_names': province_names,
                'city_names': city_names,
                'district_names': district_names,
                'plat_order_no': plat_order_no,
                'author_name': author_name,
                'salesman_name': salesman_name,
                'oms_order_no': oms_order_no,
                'next_request_id': next_request_id,
            }
            _inputs = {k: v for k, v in _inputs.items() if v is not None}
            _emit_debug(f"      [REQUEST DEBUG] query() 入参: {_summarize_debug_dict(_inputs)}")

        sign_params = {
            'appId': self.hjy_app_id,
            'sid': self.hjy_sid,
            'startBusinessTime': start_business_time,
            'endBusinessTime': end_business_time,
        }
        for key, values in (
            ('shopNo', shop_no),
            ('warehouseNo', warehouse_no),
            ('specNo', spec_no),
            ('summaryNo', summary_no),
            ('omsStockoutNo', oms_stockout_no),
            ('provinceNames', province_names),
            ('cityNames', city_names),
            ('districtNames', district_names),
            ('platOrderNo', plat_order_no),
            ('omsOrderNo', oms_order_no),
        ):
            v = self._format_array_param(values)
            if v:
                sign_params[key] = v
        if author_name:
            sign_params['authorName'] = author_name
        if salesman_name:
            sign_params['salesmanName'] = salesman_name
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
            _emit_debug(f"      [API DEBUG] sign_params: {_summarize_debug_dict(sign_params)}")
            hs = api_params.get('hjySign') or ''
            _emit_debug(
                f"      [API DEBUG] hjySign={_summarize_debug_value(hs, max_len=16)}, "
                f"top_sign={str(top_sign)[:16]}...<{len(str(top_sign))} chars>"
            )

        return self._request_once(api_params, sys_params, debug=debug)

    def query_all(
        self,
        start_business_time: str,
        end_business_time: str,
        shop_no: Optional[List[str]] = None,
        warehouse_no: Optional[List[str]] = None,
        spec_no: Optional[List[str]] = None,
        summary_no: Optional[List[str]] = None,
        oms_stockout_no: Optional[List[str]] = None,
        province_names: Optional[List[str]] = None,
        city_names: Optional[List[str]] = None,
        district_names: Optional[List[str]] = None,
        plat_order_no: Optional[List[str]] = None,
        author_name: Optional[str] = None,
        salesman_name: Optional[str] = None,
        oms_order_no: Optional[List[str]] = None,
        debug: bool = False,
    ) -> List[Dict]:
        all_data: List[Dict] = []
        next_request_id = None
        page_no = 0
        while True:
            page_no += 1
            if debug:
                _emit_debug(f"    [DEBUG] 查询第 {page_no} 页...")
            result = self.query(
                start_business_time=start_business_time,
                end_business_time=end_business_time,
                shop_no=shop_no,
                warehouse_no=warehouse_no,
                spec_no=spec_no,
                summary_no=summary_no,
                oms_stockout_no=oms_stockout_no,
                province_names=province_names,
                city_names=city_names,
                district_names=district_names,
                plat_order_no=plat_order_no,
                author_name=author_name,
                salesman_name=salesman_name,
                oms_order_no=oms_order_no,
                next_request_id=next_request_id,
                debug=debug,
            )
            if str(result.get('resultCode')) != '200':
                if debug:
                    _emit_debug(f"    [DEBUG] 查询失败: {result.get('message')}")
                break
            data_list = result.get('data', []) or []
            page_count = len(data_list)
            if data_list:
                all_data.extend(data_list)
            next_request_id = result.get('nextRequestId')
            if debug:
                _emit_debug(
                    f"    [PROGRESS] 页={page_no}, 本页={page_count}, 累计={len(all_data)}, "
                    f"nextRequestId={next_request_id}"
                )
            if not next_request_id or next_request_id == 'false':
                break
            time.sleep(0.1)
        if debug:
            _emit_debug(f"    [DEBUG] 查询完成，共 {len(all_data)} 条")
        return all_data
