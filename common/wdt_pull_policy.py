# -*- coding: utf-8 -*-
"""旺店通/慧经营：仅支持按日查询的拉取服务（不可按小时切分）。"""

from datetime import datetime, timedelta
from typing import FrozenSet, Tuple

# 接口参数为 eventDay / businessDate / startDate+endDate（日粒度），传 interval 会重复拉同一天
WDT_DAY_ONLY_PULL_SERVICES: FrozenSet[str] = frozenset({
    'marketing_share_result',
    'expense_sku_day_summary',
    'expense_sku_share_day_detail',
    'profits_sku',
    'profits_order',
    'profits_live_sku',
    'profits_live_order',
    'profits_live_refund',
})


def is_wdt_day_only_service(service_name: str) -> bool:
    return bool(service_name) and service_name in WDT_DAY_ONLY_PULL_SERVICES


def profits_live_query_date_range(start_time: str, end_time: str = '') -> Tuple[str, str]:
    """
    profits_live_order / profits_live_refund 接口日期参数：
    每次按 startDate=n、endDate=n+1 查询（左闭右开），而非 start/end 都用 n。
    """
    start_date = start_time.split(' ')[0] if ' ' in start_time else start_time[:10]
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = (start_dt + timedelta(days=1)).strftime('%Y-%m-%d')
    return start_date, end_date
