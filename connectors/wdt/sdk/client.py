#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
奇门API客户端模块
封装通用的请求逻辑
"""

import json
import time
import requests
from urllib.parse import urlencode
from typing import Dict, Any, Optional, List

from .config import WdtConfig
from .sign import WdtSignUtil


def _get_debug_print():
    """获取带时间戳的 debug_print 函数"""
    try:
        from utils.logger import debug_print
        return debug_print
    except ImportError:
        # 如果导入失败，返回普通 print
        return lambda msg, end='\n', flush=False: print(f"      {msg}", end=end, flush=flush)


class QimenClient:
    """
    奇门API客户端基类
    
    处理通用的请求签名、发送和响应解析逻辑
    """
    
    def __init__(self, config: Optional[WdtConfig] = None):
        """
        初始化客户端
        
        Args:
            config: 配置对象，为None时使用默认配置
        """
        self.config = config or WdtConfig.default()
    
    def _build_api_params(self, params: Dict, pager: Dict, timestamp: str) -> Dict:
        """
        构建API业务参数
        
        Args:
            params: 业务查询参数
            pager: 分页参数
            timestamp: 时间戳
            
        Returns:
            API参数字典
        """
        cleaned = {k: v for k, v in (params or {}).items() if v is not None}
        return {
            'params': json.dumps(cleaned, ensure_ascii=False),
            'pager': json.dumps(pager, ensure_ascii=False),
            'datetime': timestamp,
            'wdt_appkey': self.config.app_key,
            'wdt_salt': self.config.wdt_salt,
            'wdt3_customer_id': self.config.wdt3_customer_id
        }
    
    def _build_sys_params(self, method: str, timestamp: str) -> Dict:
        """
        构建系统参数
        
        Args:
            method: API方法名
            timestamp: 时间戳
            
        Returns:
            系统参数字典
        """
        return {
            'app_key': self.config.qimen_appkey,
            'v': '2.0',
            'format': 'json',
            'sign_method': 'md5',
            'method': method,
            'timestamp': timestamp,
            'target_app_key': self.config.target_appkey,
            'session': ''
        }
    
    def call(self, method: str, params: Dict, pager: Optional[Dict] = None, 
             debug: bool = False, max_retries: int = 5, retry_delay: float = 1.0) -> Dict:
        """
        调用奇门API（带重试机制）
        
        Args:
            method: API方法名（如 wdt.wms.stockout.sales.querywithdetail）
            params: 业务查询参数
            pager: 分页参数，默认 {'page_size': 20, 'page_no': 1}
            debug: 是否打印调试信息
            max_retries: 最大重试次数（默认3次）
            retry_delay: 重试间隔秒数（默认1秒）
            
        Returns:
            API响应结果
        """
        pager = pager or {'page_size': 20, 'page_no': 1}
        debug_print = _get_debug_print()
        
        if debug:
            debug_print(f"  [API] {method} pager={pager} params={params}")
        
        last_result = None
        
        for attempt in range(max_retries):
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            t0 = time.time()
            
            # 构建参数
            api_params = self._build_api_params(params, pager, timestamp)
            sys_params = self._build_sys_params(method, timestamp)
            
            # 生成旺店通签名
            wdt_sign = WdtSignUtil.generate_wdt_sign(
                api_params, method, self.config.wdt_secret
            )
            api_params['wdt_sign'] = wdt_sign
            
            # 生成淘宝奇门签名
            top_sign = WdtSignUtil.generate_top_sign(
                {**sys_params, **api_params}, self.config.qimen_appsecret
            )
            sys_params['sign'] = top_sign
            
            # 构建请求URL
            request_url = f"{self.config.gateway_url}?{urlencode({k: str(v) for k, v in sys_params.items()})}"
            
            try:
                response = requests.post(
                    request_url,
                    data=api_params,
                    headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
                    timeout=self.config.timeout
                )
                
                result = response.json()
                last_result = result.get('response', result)
                
                if debug:
                    elapsed = time.time() - t0
                    debug_print(
                        f"  [API] {method} http={response.status_code} "
                        f"status={last_result.get('status')} msg={last_result.get('message')} "
                        f"elapsed={elapsed:.2f}s"
                    )
                    if last_result.get('status') is None:
                        import json as _json
                        debug_print(f"  [API] 完整响应: {_json.dumps(last_result, ensure_ascii=False)}")
                
                # 检查是否需要重试（status为None表示服务端错误）
                status = last_result.get('status')
                if status is not None:
                    # 成功获取响应，返回结果
                    return last_result
                
                if attempt < max_retries - 1:
                    if debug:
                        debug_print(f"  [API] status=None, 第{attempt + 1}次重试")
                    time.sleep(retry_delay * (attempt + 1))
                
            except requests.exceptions.RequestException as e:
                last_result = {
                    'status': 'error',
                    'message': f'网络请求异常: {str(e)}'
                }
                if attempt < max_retries - 1:
                    if debug:
                        debug_print(f"  [API] 网络异常 第{attempt + 1}次重试: {e}")
                    time.sleep(retry_delay * (attempt + 1))
                    
            except json.JSONDecodeError:
                last_result = {
                    'status': 'error',
                    'message': '响应不是有效的JSON格式',
                    'raw_response': response.text
                }
                # JSON解析错误不重试
                break
        
        return last_result
    
    def call_all_pages(self, method: str, params: Dict, 
                       page_size: int = 50, max_pages: Optional[int] = None) -> List[Dict]:
        """
        分页调用API，获取所有数据
        
        Args:
            method: API方法名
            params: 业务查询参数
            page_size: 每页数量
            max_pages: 最大页数限制，None表示获取全部
            
        Returns:
            所有数据列表
        """
        all_data = []
        page_no = 1
        
        while True:
            if max_pages and page_no > max_pages:
                break
            
            pager = {'page_size': page_size, 'page_no': page_no}
            result = self.call(method, params, pager)
            
            # 检查响应状态 (status可能是int或str)
            if str(result.get('status')) != '0':
                break
            
            # 获取数据
            data = result.get('data', {})
            items = data.get('order', []) or data.get('data', [])
            
            if not items:
                break
            
            all_data.extend(items)
            
            # 检查是否还有下一页
            total_count = int(data.get('total_count', 0))
            if len(all_data) >= total_count:
                break
            
            page_no += 1
        
        return all_data

