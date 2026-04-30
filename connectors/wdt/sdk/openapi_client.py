# -*- coding: utf-8 -*-

import json
import time
import hashlib
import requests
from urllib.parse import urlencode
from typing import Dict, Any, Optional

from .config import WdtConfig


def _get_debug_print():
    try:
        from utils.logger import debug_print
        return debug_print
    except ImportError:
        return lambda msg, end='\n', flush=False: print(f"      {msg}", end=end, flush=flush)


class OpenAPIClient:
    
    GATEWAY_URL = 'http://wdt.wangdian.cn/openapi'
    
    def __init__(self, config: Optional[WdtConfig] = None):
        self.config = config or WdtConfig.default()
    
    def _generate_sign(self, params: Dict, secret: str) -> str:
        sign_str = ''.join(f"{k}{params[k]}" for k in sorted(params.keys()))
        full_str = secret + sign_str + secret
        return hashlib.md5(full_str.encode('utf-8')).hexdigest()
    
    def call(self, method: str, params: Dict, pager: Optional[Dict] = None,
             debug: bool = False) -> Dict:
        pager = pager or {'page_size': 20, 'page_no': 0}
        debug_print = _get_debug_print()
        timestamp = int(time.time()) - 1325347200
        
        body_json = json.dumps(params, ensure_ascii=False)
        page_size = str(pager.get('page_size', 20))
        page_no = str(pager.get('page_no', 0))
        calc_total = str(pager.get('calc_total', 1))
        
        sign_params = {
            'method': method,
            'v': '1.0',
            'timestamp': str(timestamp),
            'sid': self.config.wdt3_customer_id,
            'key': self.config.app_key,
            'salt': self.config.wdt_salt,
            'body': body_json,
            'page_size': page_size,
            'page_no': page_no,
            'calc_total': calc_total,
        }
        
        sign = self._generate_sign(sign_params, self.config.wdt_secret)
        
        url_params = {
            'method': method,
            'v': '1.0',
            'timestamp': str(timestamp),
            'sid': self.config.wdt3_customer_id,
            'key': self.config.app_key,
            'salt': self.config.wdt_salt,
            'sign': sign,
            'page_size': page_size,
            'page_no': page_no,
            'calc_total': calc_total,
        }
        request_url = f"{self.GATEWAY_URL}?{urlencode(url_params)}"
        
        if debug:
            debug_print(f"      [API DEBUG] method: {method}")
            debug_print(f"      [API DEBUG] params: {params}")
            debug_print(f"      [API DEBUG] pager: {pager}")
        
        try:
            if debug:
                debug_print(f"      [API DEBUG] 发送请求中... (超时: {self.config.timeout}秒)")
            
            response = requests.post(
                request_url,
                data=body_json,
                headers={'Content-Type': 'application/json'},
                timeout=self.config.timeout
            )
            
            if debug:
                debug_print(f"      [API DEBUG] HTTP状态码: {response.status_code}")
            
            result = response.json()
            
            if debug:
                debug_print(f"      [API DEBUG] API status: {result.get('status')}, message: {result.get('message')}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            return {'status': 'error', 'message': f'网络请求异常: {str(e)}'}
        except json.JSONDecodeError:
            return {'status': 'error', 'message': '响应不是有效的JSON格式'}
