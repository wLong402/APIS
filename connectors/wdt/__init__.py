# -*- coding: utf-8 -*-
"""
旺店通连接器

提供旺店通奇门接口的数据拉取能力
"""

from .client import WdtClient
from .services import (
    TradePullService,
    RefundPullService,
    AftersalesRefundPullService,
    StockoutSalesQueryWithDetailPullService,
    ErpTradePullService,
    StockinRefundQueryWithDetailPullService,
    StockSpecPullService,
    BillStandardPullService,
    BkShareDataPullService,
    FixbillDataSummaryPullService,
    MarketingDetailPullService,
    HistoryTradePullService,
    ProfitsSkuPullService,
    ProfitsOrderPullService,
    ShtReconDetailPullService,
    ReconDeliveryDetailPullService,
    HjyDeliveryDetailPullService,
    ReconOrderConfirmSummaryPullService,
    ReconDztkSummaryPullService,
    ProfitsLiveSkuPullService,
    ProfitsLiveOrderPullService,
    ProfitsLiveRefundPullService,
    MarketingShareResultPullService,
    ExpenseSkuDaySummaryPullService,
    ExpenseSkuShareDayDetailPullService,
    LogisticsTracePullService,
    WarehousePullService,
    GoodsQueryWithSpecPullService,
    StockinRefundOpenAPIPullService,
)
from .repositories import (
    TradeRepository,
    RefundRepository,
    StockoutSalesDetailRepository,
    ErpTradeRepository,
    StockinRefundDetailRepository,
    StockSpecRepository,
    BillStandardRepository,
    BkShareDataRepository,
    FixbillDataSummaryRepository,
    MarketingDetailRepository,
    HistoryTradeRepository,
    ProfitsSkuRepository,
    ProfitsOrderRepository,
    ShtReconDetailRepository,
    ReconDeliveryDetailRepository,
    HjyDeliveryDetailRepository,
    ReconOrderConfirmSummaryRepository,
    ReconDztkSummaryRepository,
    ProfitsLiveSkuRepository,
    ProfitsLiveOrderRepository,
    ProfitsLiveRefundRepository,
    MarketingShareResultRepository,
    ExpenseSkuDaySummaryRepository,
    ExpenseSkuShareDayDetailRepository,
    LogisticsTraceRepository,
    WarehouseRepository,
)

# 连接器元信息
CONNECTOR_INFO = {
    'name': 'wdt',
    'display_name': '旺店通',
    'description': '旺店通ERP系统数据拉取',
    'version': '1.0.0',
    'services': {
        'trade': {
            'name': '原始订单',
            'class': TradePullService,
        },
        'refund': {
            'name': '退款单',
            'class': RefundPullService,
        },
        'aftersales_refund': {
            'name': '售后退款单',
            'class': AftersalesRefundPullService,
        },
        'stockout_sales_query_with_detail': {
            'name': '销售出库单查询（带明细）',
            'class': StockoutSalesQueryWithDetailPullService,
        },
        'erp_trade': {
            'name': 'ERP订单',
            'class': ErpTradePullService,
        },
        'erp': {
            'name': 'ERP订单',
            'class': ErpTradePullService,
        },
        'stockin_refund_query_with_detail': {
            'name': '退货入库单查询（带明细）',
            'class': StockinRefundQueryWithDetailPullService,
        },
        'stockspec': {
            'name': '库存规格',
            'class': StockSpecPullService,
        },
        'history_trade': {
            'name': '历史订单',
            'class': HistoryTradePullService,
        },
        'logistics_trace': {
            'name': '物流轨迹查询',
            'class': LogisticsTracePullService,
        },
        'warehouse': {
            'name': '仓库档案',
            'class': WarehousePullService,
        },
        'goods_query_with_spec': {
            'name': '货品档案(含规格)',
            'class': GoodsQueryWithSpecPullService,
        },
        'stockin_refund_openapi': {
            'name': '退货入库单(OpenAPI)',
            'class': StockinRefundOpenAPIPullService,
        },
    },
}


def get_service(service_name: str):
    """
    获取服务类
    
    Args:
        service_name: 服务名称（trade/refund/stockout/erp_trade）
        
    Returns:
        服务类
    """
    service_info = CONNECTOR_INFO['services'].get(service_name)
    if service_info:
        return service_info['class']
    return None


def create_service(service_name: str, **kwargs):
    """
    创建服务实例
    
    Args:
        service_name: 服务名称
        **kwargs: 传递给服务构造函数的参数
        
    Returns:
        服务实例
    """
    service_cls = get_service(service_name)
    if service_cls:
        return service_cls(**kwargs)
    raise ValueError(f"未知的服务: {service_name}")


__all__ = [
    # 客户端
    'WdtClient',
    # 服务
    'TradePullService',
    'RefundPullService',
    'AftersalesRefundPullService', 
    'StockoutSalesQueryWithDetailPullService',
    'ErpTradePullService',
    'StockinRefundQueryWithDetailPullService',
    'StockSpecPullService',
    'BillStandardPullService',
    'BkShareDataPullService',
    'FixbillDataSummaryPullService',
    'MarketingDetailPullService',
    'HistoryTradePullService',
    'ProfitsSkuPullService',
    'ProfitsOrderPullService',
    'ShtReconDetailPullService',
    'ReconDeliveryDetailPullService',
    'HjyDeliveryDetailPullService',
    'ReconOrderConfirmSummaryPullService',
    'ReconDztkSummaryPullService',
    'ProfitsLiveSkuPullService',
    'ProfitsLiveOrderPullService',
    'ProfitsLiveRefundPullService',
    'MarketingShareResultPullService',
    'ExpenseSkuDaySummaryPullService',
    'ExpenseSkuShareDayDetailPullService',
    'LogisticsTracePullService',
    'WarehousePullService',
    'GoodsQueryWithSpecPullService',
    'StockinRefundOpenAPIPullService',
    # 仓库
    'TradeRepository',
    'RefundRepository',
    'StockoutSalesDetailRepository',
    'ErpTradeRepository',
    'StockinRefundDetailRepository',
    'StockSpecRepository',
    'BillStandardRepository',
    'BkShareDataRepository',
    'FixbillDataSummaryRepository',
    'MarketingDetailRepository',
    'HistoryTradeRepository',
    'ProfitsSkuRepository',
    'ProfitsOrderRepository',
    'ShtReconDetailRepository',
    'ReconDeliveryDetailRepository',
    'HjyDeliveryDetailRepository',
    'ReconOrderConfirmSummaryRepository',
    'ReconDztkSummaryRepository',
    'ProfitsLiveSkuRepository',
    'ProfitsLiveOrderRepository',
    'ProfitsLiveRefundRepository',
    'MarketingShareResultRepository',
    'ExpenseSkuDaySummaryRepository',
    'ExpenseSkuShareDayDetailRepository',
    'LogisticsTraceRepository',
    'WarehouseRepository',
    # 元信息
    'CONNECTOR_INFO',
    # 工厂方法
    'get_service',
    'create_service',
]

