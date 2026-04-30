# -*- coding: utf-8 -*-
"""
微伴底层 API 客户端
"""

import json
import time
import requests
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from .config import WeibanConfig


class WeibanAPIClient:
    """
    微伴底层 API 客户端
    
    负责 HTTP 请求发送和响应处理，自动管理 access_token
    """
    
    def __init__(self, config: Optional[WeibanConfig] = None):
        """
        初始化客户端
        
        Args:
            config: 配置对象，为 None 时使用默认配置
        """
        self.config = config or WeibanConfig()
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        self._access_token: Optional[str] = None
    
    def _get_access_token(self) -> Tuple[str, int]:
        """
        内部方法：从微伴 API 获取新的 access_token
        
        Returns:
            (access_token, expires_in) 元组
            
        Raises:
            RuntimeError: 获取 access_token 失败
        """
        url = f"{self.config.base_url}/open-api/access_token/get"
        values = {
            'corp_id': self.config.corp_id,
            'secret': self.config.secret,
        }
        
        try:
            resp = self.session.post(url, json=values, timeout=self.config.timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"获取 access_token 失败: {e}")
        
        if isinstance(data, dict) and data.get("errcode") == 0 and "access_token" in data:
            return data["access_token"], int(data.get("expires_in", 7200))
        
        raise RuntimeError(f"获取 access_token 失败: {data.get('errmsg', '未知错误')}")
    
    def get_access_token(self) -> str:
        """
        获取 access_token，优先从本地缓存文件读取，过期则重新获取并刷新缓存
        
        Returns:
            access_token 字符串
            
        Raises:
            RuntimeError: 获取 access_token 失败
        """
        cache_path = Path(self.config.token_cache_path)
        cached = {}  # 默认值
        
        # 尝试从缓存读取
        try:
            if cache_path.exists():
                with open(cache_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        cached = json.loads(content) or {}
        except Exception:
            cached = {}
        
        now = time.time()
        
        # 检查缓存是否存在且未过期（提前 60 秒刷新）
        if (isinstance(cached, dict) and 
            cached.get('access_token') and 
            cached.get('expires_at') and 
            now < float(cached['expires_at']) - 60):
            self._access_token = cached['access_token']
            return self._access_token
        
        # 缓存无效，重新获取
        token, ttl = self._get_access_token()
        expires_at = now + float(ttl)
        
        # 写入缓存
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'access_token': token,
                    'expires_at': expires_at
                }, ensure_ascii=False))
        except Exception as e:
            # 缓存写入失败不影响 token 使用
            pass
        
        self._access_token = token
        return token
    
    def get(self, endpoint: str, params: Dict[str, Any] = None, 
            debug: bool = False) -> Dict[str, Any]:
        """
        发送 GET 请求
        
        Args:
            endpoint: API 端点（不含基础 URL）
            params: 查询参数
            debug: 是否打印调试信息
            
        Returns:
            API 响应字典
        """
        url = f"{self.config.base_url}{endpoint}"
        
        # 自动获取 access_token
        access_token = self.get_access_token()
        
        # 添加 access_token
        if params is None:
            params = {}
        params['access_token'] = access_token
        
        if debug:
            print(f"  [DEBUG] GET {url}")
            print(f"  [DEBUG] Params: {params}")
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            # 如果 token 过期，尝试刷新一次
            if data.get('errcode') == 40014 or data.get('errcode') == 42001:  # token 过期
                if debug:
                    print(f"  [DEBUG] Token 过期，尝试刷新...")
                # 清除缓存并重新获取
                cache_path = Path(self.config.token_cache_path)
                if cache_path.exists():
                    cache_path.unlink()
                access_token = self.get_access_token()
                params['access_token'] = access_token
                # 重试请求
                response = self.session.get(url, params=params, timeout=self.config.timeout)
                response.raise_for_status()
                data = response.json()
            
            if debug:
                print(f"  [DEBUG] Response: errcode={data.get('errcode')}, errmsg={data.get('errmsg')}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            if debug:
                print(f"  [DEBUG] Request failed: {e}")
            raise
    
    def post(self, endpoint: str, data: Dict[str, Any] = None,
             params: Dict[str, Any] = None, debug: bool = False) -> Dict[str, Any]:
        """
        发送 POST 请求
        
        Args:
            endpoint: API 端点
            data: 请求体数据
            params: 查询参数
            debug: 是否打印调试信息
            
        Returns:
            API 响应字典
        """
        url = f"{self.config.base_url}{endpoint}"
        
        # 自动获取 access_token
        access_token = self.get_access_token()
        
        # 添加 access_token 到查询参数
        if params is None:
            params = {}
        params['access_token'] = access_token
        
        if debug:
            print(f"  [DEBUG] POST {url}")
            print(f"  [DEBUG] Params: {params}")
            print(f"  [DEBUG] Data: {data}")
        
        try:
            response = self.session.post(
                url,
                json=data,
                params=params,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            # 如果 token 过期，尝试刷新一次
            if result.get('errcode') == 40014 or result.get('errcode') == 42001:  # token 过期
                if debug:
                    print(f"  [DEBUG] Token 过期，尝试刷新...")
                # 清除缓存并重新获取
                cache_path = Path(self.config.token_cache_path)
                if cache_path.exists():
                    cache_path.unlink()
                access_token = self.get_access_token()
                params['access_token'] = access_token
                # 重试请求
                response = self.session.post(url, json=data, params=params, timeout=self.config.timeout)
                response.raise_for_status()
                result = response.json()
            
            return result
            
        except requests.exceptions.RequestException as e:
            if debug:
                print(f"  [DEBUG] Request failed: {e}")
            raise

