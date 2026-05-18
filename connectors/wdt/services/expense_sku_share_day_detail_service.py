# -*- coding: utf-8 -*-

import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict

from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import ExpenseSkuShareDayDetailRepository
from ..sdk.api import ExpenseSkuShareDayDetailQueryAPI


class ExpenseSkuShareDayDetailPullService(BasePullService):
    SERVICE_NAME = 'expense_sku_share_day_detail'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'expense_sku_share_day_detail_query'

    def __init__(self, client: WdtClient = None, repository: ExpenseSkuShareDayDetailRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or ExpenseSkuShareDayDetailRepository()
        super().__init__(self.client, self.repo)

    @property
    def expense_sku_share_day_detail_api(self) -> ExpenseSkuShareDayDetailQueryAPI:
        return self.client.expense_sku_share_day_detail_api

    @staticmethod
    def _build_row_key(item: Dict) -> str:
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
        end_date = end_time.split(' ')[0] if ' ' in end_time else end_time

        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            ed = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            sd = ed = datetime.strptime(start_date, '%Y-%m-%d')

        debug = kwargs.get('debug', False)
        shop_arg = kwargs.get('shop_no') or kwargs.get('shop_nos')
        summary_arg = kwargs.get('summary_no')

        all_data: List[Dict] = []
        cur = sd
        while cur <= ed:
            day = cur.strftime('%Y-%m-%d')
            if debug:
                print(f"    [DEBUG] 拉取 businessDate={day}")
            data = self.expense_sku_share_day_detail_api.query_all(
                business_date=day,
                shop_no=shop_arg,
                summary_no=summary_arg,
                debug=debug,
            )
            all_data.extend(data)
            cur += timedelta(days=1)

        for item in all_data:
            item['rowKey'] = self._build_row_key(item)

        return all_data
