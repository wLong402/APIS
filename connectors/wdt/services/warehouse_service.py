# -*- coding: utf-8 -*-

from typing import List, Dict

from core.logger import debug_print
from common.base_service import BasePullService
from ..client import WdtClient, get_wdt_client
from ..repositories import WarehouseRepository
from ..sdk.api import QueryWarehouseAPI


class WarehousePullService(BasePullService):

    SERVICE_NAME = 'warehouse'
    SYSTEM_NAME = 'wdt'
    API_NAME = 'query_warehouse'

    def __init__(self, client: WdtClient = None, repository: WarehouseRepository = None):
        self.client = client or get_wdt_client()
        self.repo = repository or WarehouseRepository()
        super().__init__(self.client, self.repo)

    @property
    def warehouse_api(self) -> QueryWarehouseAPI:
        return self.client.warehouse_api

    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        debug = kwargs.get('debug', False)
        page_size = kwargs.get('page_size', 200)

        type_ = kwargs.get('type')
        if type_ is not None and type_ != '':
            type_ = int(type_)

        sub_type = kwargs.get('sub_type')
        if sub_type is not None and sub_type != '':
            sub_type = int(sub_type)

        hide_delete = kwargs.get('hide_delete')
        if hide_delete is None or hide_delete == '':
            hide_delete = 0
        else:
            hide_delete = int(hide_delete)

        if debug:
            debug_print(f"    [DEBUG] 调用 API: {self.warehouse_api.METHOD}")

        return self.warehouse_api.query_all(
            start_time=start_time,
            end_time=end_time,
            warehouse_no=kwargs.get('warehouse_no'),
            warehouse_name=kwargs.get('warehouse_name'),
            type=type_,
            sub_type=sub_type,
            hide_delete=hide_delete,
            page_size=page_size,
            debug=debug,
        )
