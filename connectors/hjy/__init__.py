# -*- coding: utf-8 -*-
"""
慧经营连接器

将 wdt.hjy.* 类接口归入本连接器，与旺店通奇门 ERP / OpenAPI 区分。
凭证默认复用配置中的 wdt:（也可单独配置 hjy:）。
"""

from .client import HjyClient, get_hjy_client
from .services import (
    ReconDeliverySummaryPullService,
    ReconReturnStorageSummaryPullService,
    ReconThrkDetailPullService,
)
from .repositories import (
    ReconDeliverySummaryRepository,
    ReconReturnStorageSummaryRepository,
    ReconThrkDetailRepository,
)

# 既有 HJY 服务实现仍在 connectors.wdt，此处仅注册到慧经营连接器
from connectors.wdt.services import (
    BillStandardPullService,
    BkShareDataPullService,
    FixbillDataSummaryPullService,
    MarketingDetailPullService,
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
)

CONNECTOR_INFO = {
    'name': 'hjy',
    'display_name': '慧经营',
    'description': '旺店通慧经营（wdt.hjy.*）数据拉取',
    'version': '1.0.0',
    'client_class': HjyClient,
    'services': {
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
        'hjy_delivery_detail': {
            'name': '慧经营发货明细',
            'class': HjyDeliveryDetailPullService,
        },
        'recon_delivery_summary': {
            'name': '发货汇总',
            'class': ReconDeliverySummaryPullService,
        },
        'recon_return_storage_summary': {
            'name': '退货入库汇总',
            'class': ReconReturnStorageSummaryPullService,
        },
        'recon_thrk_detail': {
            'name': '退货入库明细',
            'class': ReconThrkDetailPullService,
        },
        'recon_order_confirm_summary': {
            'name': '对账正应收汇总',
            'class': ReconOrderConfirmSummaryPullService,
        },
        'recon_dztk_summary': {
            'name': '对账退款汇总',
            'class': ReconDztkSummaryPullService,
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
        'expense_sku_share_day_detail': {
            'name': '账单分摊日明细',
            'class': ExpenseSkuShareDayDetailPullService,
        },
    },
}


def get_service(service_name: str):
    service_info = CONNECTOR_INFO['services'].get(service_name)
    if service_info:
        return service_info['class']
    return None


def create_service(service_name: str, **kwargs):
    service_cls = get_service(service_name)
    if service_cls:
        return service_cls(**kwargs)
    raise ValueError(f"未知的慧经营服务: {service_name}")


__all__ = [
    'HjyClient',
    'get_hjy_client',
    'CONNECTOR_INFO',
    'get_service',
    'create_service',
    'ReconDeliverySummaryPullService',
    'ReconReturnStorageSummaryPullService',
    'ReconThrkDetailPullService',
    'ReconDeliverySummaryRepository',
    'ReconReturnStorageSummaryRepository',
    'ReconThrkDetailRepository',
]
