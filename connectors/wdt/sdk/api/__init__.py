# -*- coding: utf-8 -*-
"""
旺店通API接口模块
"""

from .stockout import (
    StockoutSalesAPI,
    StockoutSalesQueryAPI,
    StockoutSalesQueryWithDetailAPI,
    StockoutOtherAPI,
    StockoutStatus,
    StockoutStatusType
)
from .stockin import (
    StockinRefundAPI,
    StockinRefundQueryAPI,
    StockinRefundQueryWithDetailAPI,
    StockinRefundStatus,
    StockinTimeType
)
from .stockspec import (
    StockSpecSearchAPI,
    StockSpecAPI
)
from .trade import (
    RawTradeSearchAPI,
    TradeQueryAPI,
    HistoryTradeQueryAPI,
    TradeStatus,
    ProcessStatus,
    PayStatus,
    RefundStatus,
    ERPTradeStatus,
    TradeType,
    TradeFrom,
    TradeTimeType
)
from .refund import (
    RawRefundSearchAPI,
    AftersalesRefundSearchAPI,
    RefundType,
    RefundPlatformStatus,
    RefundProcessStatus,
    RefundTimeType
)
from .bill import BillStandardQueryAPI
from .marketing_detail import MarketingDetailQueryAPI
from .bk_share_data import BkShareDataQueryAPI
from .fixbill_data_summary import FixbillDataSummaryQueryAPI
from .profits_sku import ProfitsSkuQueryAPI
from .profits_order import ProfitsOrderQueryAPI
from .sht_recon_detail import ShtReconDetailQueryAPI
from .recon_delivery_detail import ReconDeliveryDetailQueryAPI
from .hjy_delivery_detail import HjyDeliveryDetailQueryAPI
from .recon_order_confirm_summary import ReconOrderConfirmSummaryQueryAPI
from .recon_dztk_summary import ReconDztkSummaryQueryAPI
from .profits_live_sku import ProfitsLiveSkuQueryAPI
from .profits_live_order import ProfitsLiveOrderQueryAPI
from .profits_live_refund import ProfitsLiveRefundQueryAPI
from .marketing_share_result import MarketingShareResultQueryAPI
from .expense_sku_day_summary import ExpenseSkuDaySummaryQueryAPI
from .expense_sku_share_day_detail import ExpenseSkuShareDayDetailQueryAPI
from .logistics_trace import SearchLogisticsTraceAPI
from .warehouse import QueryWarehouseAPI
from .goods import QueryGoodsWithSpecAPI
from .stockin_refund_openapi import QueryStockinRefundOpenAPI

__all__ = [
    # 出库单API
    'StockoutSalesAPI',
    'StockoutSalesQueryAPI',
    'StockoutSalesQueryWithDetailAPI',
    'StockoutOtherAPI',
    'StockoutStatus',
    'StockoutStatusType',
    # 入库单API
    'StockinRefundAPI',
    'StockinRefundQueryAPI',
    'StockinRefundQueryWithDetailAPI',
    'StockinRefundStatus',
    'StockinTimeType',
    # 库存规格API
    'StockSpecSearchAPI',
    'StockSpecAPI',
    # 原始订单API
    'RawTradeSearchAPI',
    # ERP订单查询API
    'TradeQueryAPI',
    'HistoryTradeQueryAPI',
    # 退款API
    'RawRefundSearchAPI',
    'AftersalesRefundSearchAPI',
    # 原始订单状态常量
    'TradeStatus',
    'ProcessStatus', 
    'PayStatus',
    'RefundStatus',
    # ERP订单状态常量
    'ERPTradeStatus',
    'TradeType',
    'TradeFrom',
    'TradeTimeType',
    # 退款状态常量
    'RefundType',
    'RefundPlatformStatus',
    'RefundProcessStatus',
    'RefundTimeType',
    # 账单API
    'BillStandardQueryAPI',
    'MarketingDetailQueryAPI',
    'BkShareDataQueryAPI',
    'FixbillDataSummaryQueryAPI',
    'ProfitsSkuQueryAPI',
    'ProfitsOrderQueryAPI',
    'ShtReconDetailQueryAPI',
    'ReconDeliveryDetailQueryAPI',
    'HjyDeliveryDetailQueryAPI',
    'ReconOrderConfirmSummaryQueryAPI',
    'ReconDztkSummaryQueryAPI',
    'ProfitsLiveSkuQueryAPI',
    'ProfitsLiveOrderQueryAPI',
    'ProfitsLiveRefundQueryAPI',
    'MarketingShareResultQueryAPI',
    'ExpenseSkuDaySummaryQueryAPI',
    'ExpenseSkuShareDayDetailQueryAPI',
    'SearchLogisticsTraceAPI',
    'QueryWarehouseAPI',
    'QueryGoodsWithSpecAPI',
    'QueryStockinRefundOpenAPI',
]
