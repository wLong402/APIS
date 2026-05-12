#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单标准查询API

慧经营账单接口
API方法: wdt.hjy.bill.billsatndard.query
"""

import hashlib
import json
import time
import requests
from typing import Dict, Optional, List
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed

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


class BillStandardQueryAPI:
    """
    账单标准查询API
    
    API方法: wdt.hjy.bill.billsatndard.query
    """
    
    METHOD = 'wdt.hjy.bill.billsatndard.query'
    PAGE_SIZE = 200
    
    def __init__(self, client: Optional[QimenClient] = None,
                 config: Optional[WdtConfig] = None,
                 hjy_app_id: str = '',
                 hjy_sid: str = '',
                 hjy_app_key: str = '',
                 hjy_gateway_url: str = ''):
        self.client = client or QimenClient(config)
        self.config = config or self.client.config
        self.hjy_app_id = hjy_app_id
        self.hjy_sid = hjy_sid
        self.hjy_app_key = hjy_app_key
        self.gateway_url = hjy_gateway_url or self.config.gateway_url
    
    def _generate_hjy_sign(self, params: Dict, app_key: str) -> str:
        """
        生成慧经营签名
        规则: MD5(key1:value1&key2:value2&...&keyN:valueN + app_key).lower()
        """
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        param_str = '&'.join(f"{k}:{v}" for k, v in sorted_params)
        param_str += app_key
        param_str = param_str.replace('"', '').replace(' ', '')
        return hashlib.md5(param_str.encode('utf-8')).hexdigest().lower()
    
    def query(self,
              business_time: str,
              shop_no: Optional[List[str]] = None,
              next_request_id: Optional[str] = None,
              debug: bool = False) -> Dict:
        """
        查询账单数据（单页）
        
        使用与 RawTradeSearchAPI 相同的参数传递方式
        """
        debug_print = _get_debug_print()
        
        # 构建业务参数（不含签名）
        sign_params = {
            'appId': self.hjy_app_id,
            'sid': self.hjy_sid,
            'businesstime': business_time
        }
        
        if shop_no:
            sign_params['shopNo'] = json.dumps(shop_no, ensure_ascii=False)
        
        if next_request_id and next_request_id != 'false':
            sign_params['nextRequestId'] = next_request_id
        
        # 生成慧经营签名
        hjy_sign = self._generate_hjy_sign(sign_params, self.hjy_app_key)
        
        biz_params = sign_params.copy()
        biz_params['hjySign'] = hjy_sign
        
        if shop_no:
            biz_params['shopNo'] = shop_no
        
        if next_request_id and next_request_id != 'false':
            biz_params['nextRequestId'] = next_request_id
        
        # 只发送文档要求的参数
        api_params = {
            'hjySign': biz_params['hjySign'],
            'appId': biz_params['appId'],
            'sid': biz_params['sid'],
            'businesstime': biz_params['businesstime']
        }
        
        if shop_no:
            api_params['shopNo'] = json.dumps(shop_no, ensure_ascii=False)
        
        if next_request_id and next_request_id != 'false':
            api_params['nextRequestId'] = next_request_id
        
        if debug:
            debug_print(f"      [API DEBUG] method: {self.METHOD}")
            debug_print(f"      [API DEBUG] params: {summarize_params(api_params)}")
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建系统参数（奇门协议）
        sys_params = {
            'app_key': self.config.qimen_appkey,
            'v': '2.0',
            'format': 'json',
            'sign_method': 'md5',
            'method': self.METHOD,
            'timestamp': timestamp,
            'target_app_key': self.config.target_appkey,
            'session': ''
        }
        
        # 生成淘宝奇门签名
        top_sign = WdtSignUtil.generate_top_sign(
            {**sys_params, **api_params}, self.config.qimen_appsecret
        )
        sys_params['sign'] = top_sign
        
        # 构建请求URL
        request_url = f"{self.gateway_url}?{urlencode({k: str(v) for k, v in sys_params.items()})}"
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        
        if debug:
            debug_print(f"      [REQUEST DEBUG] method=POST, params={summarize_params(api_params)}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    request_url,
                    data=api_params,
                    headers=headers,
                    timeout=self.config.timeout
                )
                
                result = response.json()
                resp_data = result.get('response', result)
                
                if debug:
                    debug_print(
                        f"      [RESPONSE DEBUG] {summarize_response(resp_data, api_params=api_params, http_status=response.status_code)}"
                    )
                
                # 检查是否需要重试（没有 resultCode 或系统繁忙）
                result_code = resp_data.get('resultCode')
                msg = resp_data.get('message', '')
                if result_code is None or '繁忙' in msg or 'busy' in msg.lower():
                    if attempt < max_retries - 1:
                        if debug:
                            debug_print(f"      [API DEBUG] 响应异常，{attempt+1}/{max_retries} 次重试...")
                        time.sleep(1)
                        continue
                
                return resp_data
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                if debug:
                    debug_print(f"      [API DEBUG] 请求失败: {e}")
                return {'resultCode': 'error', 'message': str(e)}
            except json.JSONDecodeError:
                return {'resultCode': 'error', 'message': '响应不是有效的JSON格式'}
        
        return {'resultCode': 'error', 'message': '重试次数用尽'}
    
    def query_all(self,
                  business_time: str,
                  shop_no: Optional[List[str]] = None,
                  debug: bool = False) -> List[Dict]:
        """查询指定日期所有账单数据（自动分页）"""
        debug_print = _get_debug_print()
        all_data = []
        next_request_id = None
        page_no = 1
        
        while True:
            if debug:
                debug_print(f"    [DEBUG] 查询第 {page_no} 页...")
            
            result = self.query(
                business_time=business_time,
                shop_no=shop_no,
                next_request_id=next_request_id,
                debug=debug
            )
            
            if result.get('resultCode') != '200':
                if debug:
                    debug_print(f"    [DEBUG] 查询失败: {result.get('message')}")
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
            debug_print(f"    [DEBUG] 查询完成，共 {len(all_data)} 条账单数据")
        return all_data
    
    def query_date_range(self,
                         start_date: str,
                         end_date: str,
                         shop_no: Optional[List[str]] = None,
                         debug: bool = False,
                         max_workers: int = 5) -> List[Dict]:
        """查询日期范围内的账单数据（按天并行）"""
        debug_print = _get_debug_print()
        from datetime import datetime, timedelta
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        dates_to_query = []
        current_dt = start_dt
        while current_dt <= end_dt:
            dates_to_query.append(current_dt.strftime('%Y-%m-%d'))
            current_dt += timedelta(days=1)
        
        if debug:
            debug_print(f"    [DEBUG] 查询 {len(dates_to_query)} 天的账单数据...")
        
        all_data = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.query_all, date_str, shop_no, False): date_str 
                for date_str in dates_to_query
            }
            
            completed = 0
            for future in as_completed(futures):
                date_str = futures[future]
                try:
                    daily_data = future.result()
                    all_data.extend(daily_data)
                except Exception as e:
                    if debug:
                        debug_print(f"    [DEBUG] {date_str} 查询失败: {e}")
                completed += 1
                if debug:
                    debug_print(f"\r    [DEBUG] 进度: {completed}/{len(dates_to_query)} | 已获取: {len(all_data)} 条", end='', flush=True)
            
            if debug:
                print()
        
        if debug:
            debug_print(f"    [DEBUG] 日期范围查询完成，共 {len(all_data)} 条")
        return all_data
