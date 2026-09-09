# -*- coding: utf-8 -*-
"""
慧经营连接器公共签名/请求工具（奇门网关 + hjySign）
"""

import hashlib
import json
import time
from typing import Dict, Optional, List, Callable
from urllib.parse import urlencode, urlparse

import requests

from connectors.wdt.sdk.client import QimenClient
from connectors.wdt.sdk.config import WdtConfig
from connectors.wdt.sdk.sign import WdtSignUtil
from connectors.wdt.sdk.api.log_template import summarize_response


def get_debug_print():
    try:
        from utils.logger import debug_print
        return debug_print
    except ImportError:
        return lambda msg, end='\n', flush=False: print(f"    {msg}", end=end, flush=flush)


def emit_debug(logger_name: str, msg: str) -> None:
    get_debug_print()(msg)
    try:
        from core.logger import get_logger
        get_logger(logger_name).info(msg)
    except Exception:
        pass


def summarize_debug_value(val, max_len: int = 96) -> str:
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


def summarize_debug_dict(d: Dict, max_len: int = 96) -> str:
    parts = []
    for k in sorted(d.keys()):
        v = d.get(k)
        if v is None:
            continue
        parts.append(f'{k}={summarize_debug_value(v, max_len=max_len)}')
    return ', '.join(parts)


def format_array_param(values: Optional[List[str]]) -> Optional[str]:
    if not values:
        return None
    cleaned = [str(v).strip() for v in values if str(v).strip()]
    if not cleaned:
        return None
    return json.dumps(cleaned, ensure_ascii=False)


def generate_hjy_sign(params: Dict, app_key: str) -> str:
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    param_str = '&'.join(f"{k}:{v}" for k, v in sorted_params)
    param_str += app_key
    param_str = param_str.replace('"', '').replace(' ', '')
    return hashlib.md5(param_str.encode('utf-8')).hexdigest().lower()


class HjyQimenAPI:
    """慧经营奇门 API 基类：业务参数 hjySign + 顶层 top_sign。"""

    METHOD: str = ''
    LOGGER_NAME: str = 'connector.hjy'
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
                    emit_debug(self.LOGGER_NAME, f"      [REQUEST DEBUG] POST gateway={host}")
                    emit_debug(
                        self.LOGGER_NAME,
                        f"      [RESPONSE DEBUG] {summarize_response(resp_data, api_params=api_params, http_status=response.status_code)}",
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

    def _call(self, sign_params: Dict, debug: bool = False) -> Dict:
        hjy_sign = generate_hjy_sign(sign_params, self.hjy_app_key)
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
            emit_debug(self.LOGGER_NAME, f"      [API DEBUG] method: {self.METHOD}")
            emit_debug(self.LOGGER_NAME, f"      [API DEBUG] sign_params: {summarize_debug_dict(sign_params)}")

        return self._request_once(api_params, sys_params, debug=debug)

    def _paginate(
        self,
        build_sign_params: Callable[[Optional[str]], Dict],
        debug: bool = False,
    ) -> List[Dict]:
        all_data: List[Dict] = []
        next_request_id = None
        page_no = 0
        while True:
            page_no += 1
            if debug:
                emit_debug(self.LOGGER_NAME, f"    [DEBUG] 查询第 {page_no} 页...")
            sign_params = build_sign_params(next_request_id)
            result = self._call(sign_params, debug=debug)
            if str(result.get('resultCode')) != '200':
                if debug:
                    emit_debug(self.LOGGER_NAME, f"    [DEBUG] 查询失败: {result.get('message')}")
                break
            data_list = result.get('data', []) or []
            if data_list:
                all_data.extend(data_list)
            next_request_id = result.get('nextRequestId')
            if debug:
                emit_debug(
                    self.LOGGER_NAME,
                    f"    [PROGRESS] 页={page_no}, 本页={len(data_list)}, 累计={len(all_data)}, "
                    f"nextRequestId={next_request_id}",
                )
            if not next_request_id or next_request_id == 'false':
                break
            time.sleep(0.1)
        if debug:
            emit_debug(self.LOGGER_NAME, f"    [DEBUG] 查询完成，共 {len(all_data)} 条")
        return all_data
