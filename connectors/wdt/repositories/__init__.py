# -*- coding: utf-8 -*-
"""
旺店通数据仓库模块
"""

from .trade_repo import TradeRepository
from .raw_trade_detail_repo import RawTradeDetailRepository
from .raw_trade_discount_list_repo import RawTradeDiscountListRepository
from .refund_repo import RefundRepository
from .raw_refund_detail_repo import RawRefundDetailRepository
from .stockout_sales_repo import StockoutSalesDetailRepository
from .stockout_sales_detail_repo import StockoutSalesDetailItemRepository
from .erp_trade_repo import ErpTradeRepository
from .erp_trade_detail_repo import ErpTradeDetailRepository
from .stockin_refund_repo import StockinRefundDetailRepository
from .stockin_refund_detail_repo import StockinRefundDetailItemRepository
from .stockin_refund_order_detail_repo import StockinRefundOrderDetailRepository
from .stockspec_repo import StockSpecRepository
from .bill_repo import BillStandardRepository
from .bk_share_data_repo import BkShareDataRepository
from .fixbill_data_summary_repo import FixbillDataSummaryRepository
from .marketing_detail_repo import MarketingDetailRepository
from .history_trade_repo import HistoryTradeRepository
from .aftersales_refund_repo import AftersalesRefundRepository
from .aftersales_refund_detail_repo import AftersalesRefundDetailRepository
from .profits_sku_repo import ProfitsSkuRepository
from .profits_order_repo import ProfitsOrderRepository
from .sht_recon_detail_repo import ShtReconDetailRepository
from .recon_delivery_detail_repo import ReconDeliveryDetailRepository
from .hjy_delivery_detail_repo import HjyDeliveryDetailRepository
from .recon_order_confirm_summary_repo import ReconOrderConfirmSummaryRepository
from .recon_dztk_summary_repo import ReconDztkSummaryRepository
from .profits_live_sku_repo import ProfitsLiveSkuRepository
from .profits_live_order_repo import ProfitsLiveOrderRepository
from .profits_live_refund_repo import ProfitsLiveRefundRepository
from .marketing_share_result_repo import MarketingShareResultRepository
from .expense_sku_day_summary_repo import ExpenseSkuDaySummaryRepository
from .expense_sku_day_summary_detail_repo import ExpenseSkuDaySummaryDetailRepository
from .expense_sku_share_day_detail_repo import ExpenseSkuShareDayDetailRepository
from .logistics_trace_repo import LogisticsTraceRepository
from .warehouse_repo import WarehouseRepository
from .goods_repo import GoodsRepository
from .goods_spec_repo import GoodsSpecRepository
from .openapi_stockin_refund_repo import (
    OpenapiStockinRefundRepository,
    OpenapiStockinRefundDetailItemRepository,
    OpenapiStockinRefundOrderDetailRepository,
)

__all__ = [
    'TradeRepository',
    'RawTradeDetailRepository',
    'RawTradeDiscountListRepository',
    'RefundRepository',
    'RawRefundDetailRepository',
    'StockoutSalesDetailRepository',
    'StockoutSalesDetailItemRepository',
    'ErpTradeRepository',
    'ErpTradeDetailRepository',
    'StockinRefundRepository',
    'StockinRefundDetailRepository',
    'StockinRefundDetailItemRepository',
    'StockinRefundOrderDetailRepository',
    'StockSpecRepository',
    'BillStandardRepository',
    'BkShareDataRepository',
    'FixbillDataSummaryRepository',
    'MarketingDetailRepository',
    'HistoryTradeRepository',
    'AftersalesRefundRepository',
    'AftersalesRefundDetailRepository',
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
    'ExpenseSkuDaySummaryDetailRepository',
    'ExpenseSkuShareDayDetailRepository',
    'LogisticsTraceRepository',
    'WarehouseRepository',
    'GoodsRepository',
    'GoodsSpecRepository',
    'OpenapiStockinRefundRepository',
    'OpenapiStockinRefundDetailItemRepository',
    'OpenapiStockinRefundOrderDetailRepository',
]

