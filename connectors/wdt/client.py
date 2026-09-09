# -*- coding: utf-8 -*-
"""
旺店通 API 客户端

封装旺店通奇门接口的调用逻辑
"""

from typing import Dict, Any, Optional

from common.base_client import BaseAPIClient
from core.config import get_config

# 底层 SDK
from .sdk import QimenClient, WdtConfig
from .sdk.openapi_client import OpenAPIClient
from .sdk.api import (
    RawTradeSearchAPI,
    RawRefundSearchAPI,
    AftersalesRefundSearchAPI,
    TradeQueryAPI,
    HistoryTradeQueryAPI,
    StockoutSalesQueryAPI,
    StockoutSalesQueryWithDetailAPI,
    StockinRefundQueryAPI,
    StockinRefundQueryWithDetailAPI,
    StockSpecSearchAPI,
    BillStandardQueryAPI,
    BkShareDataQueryAPI,
    FixbillDataSummaryQueryAPI,
    ProfitsSkuQueryAPI,
    ProfitsOrderQueryAPI,
    ShtReconDetailQueryAPI,
    ReconDeliveryDetailQueryAPI,
    HjyDeliveryDetailQueryAPI,
    ReconOrderConfirmSummaryQueryAPI,
    ReconDztkSummaryQueryAPI,
    ProfitsLiveSkuQueryAPI,
    ProfitsLiveOrderQueryAPI,
    ProfitsLiveRefundQueryAPI,
    MarketingShareResultQueryAPI,
    ExpenseSkuDaySummaryQueryAPI,
    ExpenseSkuShareDayDetailQueryAPI,
    SearchLogisticsTraceAPI,
    QueryWarehouseAPI,
    QueryGoodsWithSpecAPI,
    QueryStockinRefundOpenAPI,
)


class WdtClient(BaseAPIClient):
    """
    旺店通 API 客户端
    
    封装各种 API 的调用，提供统一的接口。
    
    使用方式:
        client = WdtClient()
        trades = client.raw_trade_api.search_all(...)
    """
    
    SYSTEM_NAME = 'wdt'
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化客户端
        
        Args:
            config: 配置字典，为空时从全局配置加载
        """
        # 加载配置
        if config is None:
            app_config = get_config()
            config = app_config.get_connector_config('wdt') or {}
        
        super().__init__(config)
        
        # 创建 WdtConfig
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
        
        # 创建底层客户端
        self._qimen_client = QimenClient(self._wdt_config)
        
        # 慧经营配置
        self._hjy_app_id = config.get('hjy_app_id', '')
        self._hjy_sid = config.get('hjy_sid', '')
        self._hjy_app_key = config.get('hjy_app_key', '')
        self._hjy_gateway_url = config.get('hjy_gateway_url', '')
        
        # 初始化各 API
        self._raw_trade_api = None
        self._raw_refund_api = None
        self._aftersales_refund_api = None
        self._trade_query_api = None
        self._history_trade_api = None
        self._stockout_api = None
        self._stockout_sales_query_with_detail_api = None
        self._stockin_refund_api = None
        self._stockin_refund_query_with_detail_api = None
        self._stockspec_api = None
        self._bill_standard_api = None
        self._bk_share_data_api = None
        self._fixbill_data_summary_api = None
        self._profits_sku_api = None
        self._profits_order_api = None
        self._sht_recon_detail_api = None
        self._recon_delivery_detail_api = None
        self._hjy_delivery_detail_api = None
        self._recon_order_confirm_summary_api = None
        self._recon_dztk_summary_api = None
        self._profits_live_sku_api = None
        self._profits_live_order_api = None
        self._profits_live_refund_api = None
        self._marketing_share_result_api = None
        self._expense_sku_day_summary_api = None
        self._expense_sku_share_day_detail_api = None
        self._logistics_trace_api = None
        self._warehouse_api = None
        self._goods_query_with_spec_api = None
        self._stockin_refund_openapi_api = None
        self._openapi_client = None
    
    def call(self, method: str, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        调用奇门 API
        
        Args:
            method: API 方法名
            params: 请求参数
            **kwargs: 其他参数（pager, debug 等）
            
        Returns:
            API 响应
        """
        pager = kwargs.pop('pager', None)
        debug = kwargs.pop('debug', False)
        return self._qimen_client.call(method, params, pager, debug=debug)
    
    @property
    def raw_trade_api(self) -> RawTradeSearchAPI:
        """原始订单 API"""
        if self._raw_trade_api is None:
            self._raw_trade_api = RawTradeSearchAPI(self._qimen_client)
        return self._raw_trade_api
    
    @property
    def raw_refund_api(self) -> RawRefundSearchAPI:
        """退款单 API"""
        if self._raw_refund_api is None:
            self._raw_refund_api = RawRefundSearchAPI(self._qimen_client)
        return self._raw_refund_api
    
    @property
    def aftersales_refund_api(self) -> AftersalesRefundSearchAPI:
        """售后退换单查询 API（使用奇门网关）"""
        if self._aftersales_refund_api is None:
            self._aftersales_refund_api = AftersalesRefundSearchAPI(self._qimen_client)
        return self._aftersales_refund_api
    
    @property
    def trade_query_api(self) -> TradeQueryAPI:
        """ERP订单查询 API"""
        if self._trade_query_api is None:
            self._trade_query_api = TradeQueryAPI(self._qimen_client)
        return self._trade_query_api
    
    @property
    def history_trade_api(self) -> HistoryTradeQueryAPI:
        if self._history_trade_api is None:
            self._history_trade_api = HistoryTradeQueryAPI(self._qimen_client)
        return self._history_trade_api
    
    @property
    def stockout_api(self) -> StockoutSalesQueryAPI:
        """销售出库单 API"""
        if self._stockout_api is None:
            self._stockout_api = StockoutSalesQueryAPI(self._qimen_client)
        return self._stockout_api
    
    @property
    def stockout_sales_query_with_detail_api(self) -> StockoutSalesQueryWithDetailAPI:
        """销售出库单查询API（带明细）"""
        if self._stockout_sales_query_with_detail_api is None:
            self._stockout_sales_query_with_detail_api = StockoutSalesQueryWithDetailAPI(self._qimen_client)
        return self._stockout_sales_query_with_detail_api
    
    @property
    def stockin_refund_api(self) -> StockinRefundQueryAPI:
        """退货入库单 API"""
        if self._stockin_refund_api is None:
            self._stockin_refund_api = StockinRefundQueryAPI(self._qimen_client)
        return self._stockin_refund_api
    
    @property
    def stockin_refund_query_with_detail_api(self) -> StockinRefundQueryWithDetailAPI:
        if self._stockin_refund_query_with_detail_api is None:
            self._stockin_refund_query_with_detail_api = StockinRefundQueryWithDetailAPI(self._qimen_client)
        return self._stockin_refund_query_with_detail_api
    
    @property
    def stockspec_api(self) -> StockSpecSearchAPI:
        """库存规格 API"""
        if self._stockspec_api is None:
            self._stockspec_api = StockSpecSearchAPI(self._qimen_client)
        return self._stockspec_api
    
    @property
    def bill_standard_api(self) -> BillStandardQueryAPI:
        """慧经营账单标准 API"""
        if self._bill_standard_api is None:
            self._bill_standard_api = BillStandardQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._bill_standard_api

    @property
    def bk_share_data_api(self) -> BkShareDataQueryAPI:
        if self._bk_share_data_api is None:
            self._bk_share_data_api = BkShareDataQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._bk_share_data_api

    @property
    def fixbill_data_summary_api(self) -> FixbillDataSummaryQueryAPI:
        if self._fixbill_data_summary_api is None:
            self._fixbill_data_summary_api = FixbillDataSummaryQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._fixbill_data_summary_api
    
    @property
    def profits_sku_api(self) -> ProfitsSkuQueryAPI:
        if self._profits_sku_api is None:
            self._profits_sku_api = ProfitsSkuQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._profits_sku_api

    @property
    def profits_order_api(self) -> ProfitsOrderQueryAPI:
        if self._profits_order_api is None:
            self._profits_order_api = ProfitsOrderQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._profits_order_api

    @property
    def sht_recon_detail_api(self) -> ShtReconDetailQueryAPI:
        if self._sht_recon_detail_api is None:
            self._sht_recon_detail_api = ShtReconDetailQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._sht_recon_detail_api

    @property
    def recon_delivery_detail_api(self) -> ReconDeliveryDetailQueryAPI:
        if self._recon_delivery_detail_api is None:
            self._recon_delivery_detail_api = ReconDeliveryDetailQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._recon_delivery_detail_api

    @property
    def hjy_delivery_detail_api(self) -> HjyDeliveryDetailQueryAPI:
        if self._hjy_delivery_detail_api is None:
            self._hjy_delivery_detail_api = HjyDeliveryDetailQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._hjy_delivery_detail_api

    @property
    def recon_order_confirm_summary_api(self) -> ReconOrderConfirmSummaryQueryAPI:
        if self._recon_order_confirm_summary_api is None:
            self._recon_order_confirm_summary_api = ReconOrderConfirmSummaryQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._recon_order_confirm_summary_api

    @property
    def recon_dztk_summary_api(self) -> ReconDztkSummaryQueryAPI:
        if self._recon_dztk_summary_api is None:
            self._recon_dztk_summary_api = ReconDztkSummaryQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._recon_dztk_summary_api

    @property
    def profits_live_sku_api(self) -> ProfitsLiveSkuQueryAPI:
        if self._profits_live_sku_api is None:
            self._profits_live_sku_api = ProfitsLiveSkuQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._profits_live_sku_api

    @property
    def profits_live_order_api(self) -> ProfitsLiveOrderQueryAPI:
        if self._profits_live_order_api is None:
            self._profits_live_order_api = ProfitsLiveOrderQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._profits_live_order_api

    @property
    def profits_live_refund_api(self) -> ProfitsLiveRefundQueryAPI:
        if self._profits_live_refund_api is None:
            self._profits_live_refund_api = ProfitsLiveRefundQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._profits_live_refund_api

    @property
    def marketing_share_result_api(self) -> MarketingShareResultQueryAPI:
        if self._marketing_share_result_api is None:
            self._marketing_share_result_api = MarketingShareResultQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._marketing_share_result_api

    @property
    def expense_sku_day_summary_api(self) -> ExpenseSkuDaySummaryQueryAPI:
        if self._expense_sku_day_summary_api is None:
            self._expense_sku_day_summary_api = ExpenseSkuDaySummaryQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._expense_sku_day_summary_api

    @property
    def expense_sku_share_day_detail_api(self) -> ExpenseSkuShareDayDetailQueryAPI:
        if self._expense_sku_share_day_detail_api is None:
            self._expense_sku_share_day_detail_api = ExpenseSkuShareDayDetailQueryAPI(
                client=self._qimen_client,
                config=self._wdt_config,
                hjy_app_id=self._hjy_app_id,
                hjy_sid=self._hjy_sid,
                hjy_app_key=self._hjy_app_key,
                hjy_gateway_url=self._hjy_gateway_url,
            )
        return self._expense_sku_share_day_detail_api

    @property
    def openapi_client(self) -> OpenAPIClient:
        if self._openapi_client is None:
            self._openapi_client = OpenAPIClient(self._wdt_config)
            gw = self.config.get('openapi_gateway_url')
            if gw:
                self._openapi_client.GATEWAY_URL = gw
        return self._openapi_client

    @property
    def logistics_trace_api(self) -> SearchLogisticsTraceAPI:
        if self._logistics_trace_api is None:
            self._logistics_trace_api = SearchLogisticsTraceAPI(
                client=self.openapi_client,
                gateway_url=self.config.get('openapi_gateway_url'),
            )
        return self._logistics_trace_api

    @property
    def warehouse_api(self) -> QueryWarehouseAPI:
        if self._warehouse_api is None:
            self._warehouse_api = QueryWarehouseAPI(
                client=self.openapi_client,
                gateway_url=self.config.get('openapi_gateway_url'),
            )
        return self._warehouse_api

    @property
    def goods_query_with_spec_api(self) -> QueryGoodsWithSpecAPI:
        if self._goods_query_with_spec_api is None:
            self._goods_query_with_spec_api = QueryGoodsWithSpecAPI(
                client=self.openapi_client,
                gateway_url=self.config.get('openapi_gateway_url'),
            )
        return self._goods_query_with_spec_api

    @property
    def stockin_refund_openapi_api(self) -> QueryStockinRefundOpenAPI:
        if self._stockin_refund_openapi_api is None:
            self._stockin_refund_openapi_api = QueryStockinRefundOpenAPI(
                client=self.openapi_client,
                config=self._wdt_config,
            )
        return self._stockin_refund_openapi_api

    def health_check(self) -> bool:
        """健康检查 - 尝试调用一个简单的 API"""
        try:
            # 尝试查询一条数据来检查连接
            result = self.raw_trade_api.search(
                start_time='2020-01-01 00:00:00',
                end_time='2020-01-01 00:00:01',
                page_size=1,
                page_no=1
            )
            return result.get('status') is not None
        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")
            return False


# 全局客户端实例
_wdt_client: Optional[WdtClient] = None


def get_wdt_client() -> WdtClient:
    """获取全局旺店通客户端"""
    global _wdt_client
    if _wdt_client is None:
        _wdt_client = WdtClient()
    return _wdt_client

