# -*- coding: utf-8 -*-
"""
旺店通数据模型

复用现有的 wdt.api 模块中的常量定义
"""

# 导出状态常量
from ..sdk.api import (
    # 订单状态
    TradeStatus,
    ProcessStatus,
    PayStatus,
    RefundStatus,
    ERPTradeStatus,
    TradeType,
    TradeFrom,
    TradeTimeType,
    # 退款状态
    RefundType,
    RefundPlatformStatus,
    RefundProcessStatus,
    RefundTimeType,
    # 出库单状态
    StockoutStatus,
    StockoutStatusType,
)

__all__ = [
    # 原始订单状态
    'TradeStatus',
    'ProcessStatus',
    'PayStatus',
    'RefundStatus',
    # ERP订单状态
    'ERPTradeStatus',
    'TradeType',
    'TradeFrom',
    'TradeTimeType',
    # 退款状态
    'RefundType',
    'RefundPlatformStatus',
    'RefundProcessStatus',
    'RefundTimeType',
    # 出库单状态
    'StockoutStatus',
    'StockoutStatusType',
]

