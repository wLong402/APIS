# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import ExpenseSkuDaySummaryRepository
from ..sdk.api import ExpenseSkuDaySummaryQueryAPI


class ExpenseSkuDaySummaryPullService(BasePullService):
    SERVICE_NAME = 'expense_sku_day_summary'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'expense_sku_day_summary_query'

    def __init__(self, client: WdtClient = None, repository: ExpenseSkuDaySummaryRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or ExpenseSkuDaySummaryRepository()
        super().__init__(self.client, self.repo)

    @property
    def expense_sku_day_summary_api(self) -> ExpenseSkuDaySummaryQueryAPI:
        return self.client.expense_sku_day_summary_api

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
        end_date = end_time.split(' ')[0] if ' ' in end_time else end_time

        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            ed = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            sd = ed = datetime.strptime(start_date, '%Y-%m-%d')

        debug = kwargs.get('debug', False)

        all_data: List[Dict] = []
        cur = sd
        while cur <= ed:
            day = cur.strftime('%Y-%m-%d')
            if debug:
                print(f"    [DEBUG] 拉取 businessDate={day}")
            data = self.expense_sku_day_summary_api.query_all(
                business_date=day,
                shop_no=kwargs.get('shop_no') or kwargs.get('shop_nos'),
                spec_no=kwargs.get('spec_no'),
                summary_no=kwargs.get('summary_no'),
                expense_item_name=kwargs.get('expense_item_name'),
                debug=debug,
            )
            all_data.extend(data)
            cur += timedelta(days=1)

        return all_data
