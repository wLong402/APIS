# -*- coding: utf-8 -*-
"""
慧经营 API 客户端

复用旺店通奇门网关与慧经营凭证（配置可落在 wdt: 或 hjy: 下）。
既有 HJY 服务仍通过 WdtClient 的对应 API 属性访问；本客户端补充新接口。
"""

from typing import Dict, Any, Optional

from common.base_client import BaseAPIClient
from core.config import get_config
from connectors.wdt.client import WdtClient, get_wdt_client
from connectors.wdt.sdk import QimenClient, WdtConfig
from .sdk.api import (
    ReconDeliverySummaryQueryAPI,
    ReconReturnStorageSummaryQueryAPI,
    ReconThrkDetailQueryAPI,
)


class HjyClient(BaseAPIClient):
    SYSTEM_NAME = 'hjy'

    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            app_config = get_config()
            config = app_config.get_connector_config('hjy') or app_config.get_connector_config('wdt') or {}

        super().__init__(config)

        self._wdt_config = WdtConfig(
            app_key=config.get('app_key', ''),
            app_secret=config.get('app_secret', ''),
            qimen_appkey=config.get('qimen_appkey', ''),
            qimen_appsecret=config.get('qimen_appsecret', ''),
            gateway_url=config.get('gateway_url', ''),
            target_appkey=config.get('target_appkey', ''),
            wdt3_customer_id=config.get('wdt3_customer_id', ''),
            timeout=config.get('timeout', 30),
        )
        self._qimen_client = QimenClient(self._wdt_config)
        self._hjy_app_id = config.get('hjy_app_id', '')
        self._hjy_sid = config.get('hjy_sid', '')
        self._hjy_app_key = config.get('hjy_app_key', '')
        self._hjy_gateway_url = config.get('hjy_gateway_url', '') or config.get('gateway_url', '')

        self._wdt_client: Optional[WdtClient] = None
        self._recon_delivery_summary_api = None
        self._recon_return_storage_summary_api = None
        self._recon_thrk_detail_api = None

    def call(self, method: str, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        return self._qimen_client.call(method, params, **kwargs)

    @property
    def wdt_client(self) -> WdtClient:
        """兼容既有 HJY 服务（仍依赖 WdtClient 上的 API 属性）。"""
        if self._wdt_client is None:
            self._wdt_client = get_wdt_client()
        return self._wdt_client

    def __getattr__(self, name: str):
        # 转发到 WdtClient，便于既有 PullService 在注入 HjyClient 时仍可用
        if name.startswith('_'):
            raise AttributeError(name)
        return getattr(self.wdt_client, name)

    def _make_hjy_api(self, api_cls):
        return api_cls(
            client=self._qimen_client,
            config=self._wdt_config,
            hjy_app_id=self._hjy_app_id,
            hjy_sid=self._hjy_sid,
            hjy_app_key=self._hjy_app_key,
            hjy_gateway_url=self._hjy_gateway_url,
        )

    @property
    def recon_delivery_summary_api(self) -> ReconDeliverySummaryQueryAPI:
        if self._recon_delivery_summary_api is None:
            self._recon_delivery_summary_api = self._make_hjy_api(ReconDeliverySummaryQueryAPI)
        return self._recon_delivery_summary_api

    @property
    def recon_return_storage_summary_api(self) -> ReconReturnStorageSummaryQueryAPI:
        if self._recon_return_storage_summary_api is None:
            self._recon_return_storage_summary_api = self._make_hjy_api(ReconReturnStorageSummaryQueryAPI)
        return self._recon_return_storage_summary_api

    @property
    def recon_thrk_detail_api(self) -> ReconThrkDetailQueryAPI:
        if self._recon_thrk_detail_api is None:
            self._recon_thrk_detail_api = self._make_hjy_api(ReconThrkDetailQueryAPI)
        return self._recon_thrk_detail_api


_hjy_client: Optional[HjyClient] = None


def get_hjy_client() -> HjyClient:
    global _hjy_client
    if _hjy_client is None:
        _hjy_client = HjyClient()
    return _hjy_client
