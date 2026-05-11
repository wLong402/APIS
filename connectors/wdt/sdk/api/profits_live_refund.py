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
from .log_template import summarize_params, summarize_response


def _get_debug_print():
    try:
        from utils.logger import debug_print
        return debug_print
    except ImportError:
        return lambda msg, end='\n', flush=False: print(f"    {msg}", end=end, flush=flush)


class ProfitsLiveRefundQueryAPI:
    METHOD = 'wdt.hjy.bac.profits.live.re.order.query'

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

    def query(
        self,
        start_date: str,
        end_date: str,
        scheme_name: str,
        terms_income: str,
        stat_mode: str,
        shop_nos: Optional[str] = None,
        order_tools: Optional[str] = None,
        cost_type: Optional[str] = None,
        next_request_id: Optional[str] = None,
        debug: bool = False,
    ) -> Dict:
        debug_print = _get_debug_print()

        sign_params = {
            'appId': self.hjy_app_id,
            'sid': self.hjy_sid,
            'startDate': start_date,
            'endDate': end_date,
            'schemeName': scheme_name,
            'termsIncome': str(terms_income),
            'statMode': str(stat_mode),
        }

        if shop_nos:
            sign_params['shopNos'] = shop_nos
        if order_tools:
            sign_params['orderTools'] = order_tools
        if cost_type is not None:
            sign_params['costType'] = str(cost_type)
        if next_request_id and next_request_id != '':
            sign_params['nextRequestId'] = next_request_id

        hjy_sign = self._generate_hjy_sign(sign_params, self.hjy_app_key)

        api_params = dict(sign_params)
        api_params['hjySign'] = hjy_sign

        if debug:
            debug_print(f"      [API DEBUG] method: {self.METHOD}")
            debug_print(f"      [API DEBUG] params: {summarize_params(api_params)}")

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
                    debug_print(
                        "      [RESPONSE DEBUG] "
                        f"http={response.status_code}, {summarize_response(resp_data)}"
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

    def query_all(
        self,
        start_date: str,
        end_date: str,
        scheme_name: str,
        terms_income: str,
        stat_mode: str,
        shop_nos: Optional[str] = None,
        order_tools: Optional[str] = None,
        cost_type: Optional[str] = None,
        debug: bool = False,
    ) -> List[Dict]:
        debug_print = _get_debug_print()
        all_data = []
        next_request_id = None
        page_no = 1

        while True:
            if debug:
                debug_print(f"    [DEBUG] 查询第 {page_no} 页...")

            result = self.query(
                start_date=start_date,
                end_date=end_date,
                scheme_name=scheme_name,
                terms_income=terms_income,
                stat_mode=stat_mode,
                shop_nos=shop_nos,
                order_tools=order_tools,
                cost_type=cost_type,
                next_request_id=next_request_id,
                debug=debug,
            )

            if result.get('resultCode') != '200':
                if debug:
                    debug_print(f"    [DEBUG] 查询失败: {result.get('message')}")
                break

            data_list = result.get('data', [])
            if data_list:
                all_data.extend(data_list)

            next_request_id = result.get('nextRequestId')
            if not next_request_id or next_request_id == '':
                break

            page_no += 1
            time.sleep(0.1)

        if debug:
            debug_print(f"    [DEBUG] 查询完成，共 {len(all_data)} 条")
        return all_data
