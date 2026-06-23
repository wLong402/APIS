# -*- coding: utf-8 -*-
"""微信小店底层 API 客户端（stable_token + 订单详情）"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

from core.logger import get_logger
from .config import WechatStoreConfig

logger = get_logger('wechat_store.client')

_TOKEN_EXPIRED_CODES = {40001, 40014, 42001}


class WechatStoreAPIClient:
    """管理 access_token 并调用微信小店订单接口。"""

    def __init__(self, config: Optional[WechatStoreConfig] = None):
        self.config = config or WechatStoreConfig()
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        self._access_token: Optional[str] = None

    def _fetch_stable_token(self) -> Tuple[str, int]:
        payload = {
            'grant_type': 'client_credential',
            'appid': self.config.appid,
            'secret': self.config.secret,
        }
        logger.info(
            'wechat_store: 请求 stable_token appid=%s url=%s',
            self.config.appid,
            self.config.stable_token_url,
        )
        try:
            resp = self.session.post(
                self.config.stable_token_url,
                json=payload,
                timeout=self.config.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise RuntimeError(f'获取微信 access_token 失败: {exc}') from exc

        if isinstance(data, dict) and data.get('access_token'):
            ttl = int(data.get('expires_in', 7200))
            logger.info('wechat_store: stable_token 获取成功 expires_in=%s', ttl)
            return data['access_token'], ttl

        errcode = data.get('errcode') if isinstance(data, dict) else None
        errmsg = data.get('errmsg', '未知错误') if isinstance(data, dict) else str(data)
        raise RuntimeError(f'获取微信 access_token 失败: errcode={errcode} errmsg={errmsg}')

    def get_access_token(self, force_refresh: bool = False) -> str:
        cache_path = Path(self.config.token_cache_path)
        cached: Dict[str, Any] = {}

        if not force_refresh:
            try:
                if cache_path.exists():
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            cached = json.loads(content) or {}
            except Exception as exc:
                logger.warning('wechat_store: 读取 token 缓存失败 path=%s err=%s', cache_path, exc)
                cached = {}

            now = time.time()
            if (
                isinstance(cached, dict)
                and cached.get('access_token')
                and cached.get('expires_at')
                and now < float(cached['expires_at']) - 60
            ):
                self._access_token = cached['access_token']
                logger.debug('wechat_store: 使用缓存 access_token path=%s', cache_path)
                return self._access_token

        token, ttl = self._fetch_stable_token()
        expires_at = time.time() + float(ttl)
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'access_token': token,
                    'expires_at': expires_at,
                }, ensure_ascii=False))
            logger.info('wechat_store: token 已写入缓存 path=%s', cache_path)
        except Exception as exc:
            logger.warning('wechat_store: token 缓存写入失败 path=%s err=%s', cache_path, exc)

        self._access_token = token
        return token

    def _invalidate_token_cache(self) -> None:
        cache_path = Path(self.config.token_cache_path)
        if cache_path.exists():
            try:
                cache_path.unlink()
                logger.info('wechat_store: 已清除 token 缓存 path=%s', cache_path)
            except Exception as exc:
                logger.warning('wechat_store: 清除 token 缓存失败 path=%s err=%s', cache_path, exc)
        self._access_token = None

    def get_order(self, order_id: str, debug: bool = False) -> Dict[str, Any]:
        order_id = str(order_id or '').strip()
        if not order_id:
            raise ValueError('order_id 不能为空')

        access_token = self.get_access_token()
        url = self.config.order_get_url
        params = {'access_token': access_token}
        payload = {'order_id': order_id}

        if debug:
            logger.info('wechat_store: POST %s order_id=%s', url, order_id)

        try:
            resp = self.session.post(
                url,
                params=params,
                json=payload,
                timeout=self.config.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.error('wechat_store: 获取订单失败 order_id=%s err=%s', order_id, exc)
            raise RuntimeError(f'获取微信订单失败 order_id={order_id}: {exc}') from exc

        errcode = data.get('errcode', 0) if isinstance(data, dict) else None
        if errcode in _TOKEN_EXPIRED_CODES:
            logger.warning('wechat_store: token 过期 errcode=%s，刷新后重试 order_id=%s', errcode, order_id)
            self._invalidate_token_cache()
            access_token = self.get_access_token(force_refresh=True)
            params = {'access_token': access_token}
            resp = self.session.post(url, params=params, json=payload, timeout=self.config.timeout)
            resp.raise_for_status()
            data = resp.json()
            errcode = data.get('errcode', 0) if isinstance(data, dict) else None

        if debug or errcode not in (0, None):
            logger.info(
                'wechat_store: get_order order_id=%s errcode=%s errmsg=%s',
                order_id,
                errcode,
                data.get('errmsg') if isinstance(data, dict) else None,
            )

        if isinstance(data, dict) and errcode not in (0, None):
            raise RuntimeError(
                f'获取微信订单失败 order_id={order_id}: errcode={errcode} errmsg={data.get("errmsg")}'
            )

        return data if isinstance(data, dict) else {}
