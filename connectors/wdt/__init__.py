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
    ProfitsLiveSkuPullService,
    ProfitsLiveOrderPullService,
    ProfitsLiveRefundPullService,
    MarketingShareResultPullService,
    ExpenseSkuDaySummaryPullService,
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
    ProfitsLiveSkuRepository,
    ProfitsLiveOrderRepository,
    ProfitsLiveRefundRepository,
    MarketingShareResultRepository,
    ExpenseSkuDaySummaryRepository,
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
        'bill_standard': {
            'name': '账单标准',
            'class': BillStandardPullService,
        },
        'bk_share_data': {
            'name': '日常记账分摊结果',
            'class': BkShareDataPullService,
        },
        'fixbill_data_summary': {
            'name': '固定费用汇总数据',
            'class': FixbillDataSummaryPullService,
        },
        'marketing_detail': {
            'name': '营销明细',
            'class': MarketingDetailPullService,
        },
        'history_trade': {
            'name': '历史订单',
            'class': HistoryTradePullService,
        },
        'profits_sku': {
            'name': '商品利润表',
            'class': ProfitsSkuPullService,
        },
        'profits_order': {
            'name': '订单利润表',
            'class': ProfitsOrderPullService,
        },
        'sht_recon_detail': {
            'name': '售后对账明细',
            'class': ShtReconDetailPullService,
        },
        'recon_delivery_detail': {
            'name': '发货对账明细',
            'class': ReconDeliveryDetailPullService,
        },
        'profits_live_sku': {
            'name': '直播商品利润表',
            'class': ProfitsLiveSkuPullService,
        },
        'profits_live_order': {
            'name': '直播订单管理（正向）',
            'class': ProfitsLiveOrderPullService,
        },
        'profits_live_refund': {
            'name': '直播订单管理（逆向）',
            'class': ProfitsLiveRefundPullService,
        },
        'marketing_share_result': {
            'name': '营销账单分摊结果',
            'class': MarketingShareResultPullService,
        },
        'expense_sku_day_summary': {
            'name': '账单商品分摊日汇总主子单',
            'class': ExpenseSkuDaySummaryPullService,
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
    'ProfitsLiveSkuPullService',
    'ProfitsLiveOrderPullService',
    'ProfitsLiveRefundPullService',
    'MarketingShareResultPullService',
    'ExpenseSkuDaySummaryPullService',
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
    'ProfitsLiveSkuRepository',
    'ProfitsLiveOrderRepository',
    'ProfitsLiveRefundRepository',
    'MarketingShareResultRepository',
    'ExpenseSkuDaySummaryRepository',
    # 元信息
    'CONNECTOR_INFO',
    # 工厂方法
    'get_service',
    'create_service',
]

