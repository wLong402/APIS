# -*- coding: utf-8 -*-
"""
仓库查询 API

setting.Warehouse.queryWarehouse - 获取ERP的仓库档案资料
"""

from typing import Dict, Optional, List
from ..openapi_client import OpenAPIClient
from ..config import WdtConfig


def _get_debug_print():
    try:
        from utils.logger import debug_print
        return debug_print
    except ImportError:
        return lambda msg, end='\n', flush=False: print(f"    {msg}", end=end, flush=flush)


class QueryWarehouseAPI:
    """
    仓库查询 API

    用于查询ERP的仓库档案资料，支持增量获取（按最后修改时间）
    API方法: setting.Warehouse.queryWarehouse

    响应数据结构:
        - status: 状态码，0表示成功
        - message: 错误信息
        - data.total_count: 结果总数
        - data.details: 仓库详情列表
    """

    METHOD = 'setting.Warehouse.queryWarehouse'

    def __init__(self, client: Optional[OpenAPIClient] = None,
                 config: Optional[WdtConfig] = None,
                 gateway_url: Optional[str] = None):
        self.client = client or OpenAPIClient(config)
        if gateway_url:
            self.client.GATEWAY_URL = gateway_url

    def query(self,
              start_time: Optional[str] = None,
              end_time: Optional[str] = None,
              warehouse_no: Optional[str] = None,
              warehouse_name: Optional[str] = None,
              type: Optional[int] = None,
              sub_type: Optional[int] = None,
              hide_delete: int = 0,
              page_size: int = 200,
              page_no: int = 0,
              debug: bool = False) -> Dict:
        """
        查询仓库档案资料

        Args:
            start_time: 开始时间（最后修改时间），格式：YYYY-MM-DD HH:MM:SS
            end_time: 结束时间（最后修改时间），格式：YYYY-MM-DD HH:MM:SS
            warehouse_no: 仓库编号
            warehouse_name: 仓库名称
            type: 类型，1:普通（内部）,2:自流转,3:平台,4:京东沧海,6:抖音云仓,124:跨境,125:代发仓,126:分销委外
            sub_type: 子类型，0:默认,1:旺店通,2:菜鸟...（详见接口文档）
            hide_delete: 是否隐藏已停用数据，0:不隐藏; 1:隐藏已删除；本封装默认传 0
            page_size: 分页大小
            page_no: 页号，从0开始
            debug: 是否打印调试信息

        Returns:
            查询结果，包含：
                - status: 状态码，0表示成功
                - data.total_count: 结果总数
                - data.details: 仓库详情列表
        """
        params = {}
        if start_time:
            params['start_time'] = start_time
        if end_time:
            params['end_time'] = end_time
        if warehouse_no:
            params['warehouse_no'] = warehouse_no
        if warehouse_name:
            params['warehouse_name'] = warehouse_name
        if type is not None:
            params['type'] = type
        if sub_type is not None:
            params['sub_type'] = sub_type
        params['hide_delete'] = hide_delete

        pager = {'page_size': page_size, 'page_no': page_no, 'calc_total': 1}
        result = self.client.call(self.METHOD, params, pager, debug=debug)

        if debug:
            debug_print = _get_debug_print()
            status_code = result.get('status')
            data = result.get('data', {})
            total = data.get('total_count', 0)
            details = data.get('details', [])
            debug_print(f"    [DEBUG] API响应: status={status_code}, total_count={total}, 本页={len(details)}条")

        return result

    def query_all(self,
                  start_time: Optional[str] = None,
                  end_time: Optional[str] = None,
                  warehouse_no: Optional[str] = None,
                  warehouse_name: Optional[str] = None,
                  type: Optional[int] = None,
                  sub_type: Optional[int] = None,
                  hide_delete: int = 0,
                  page_size: int = 200,
                  debug: bool = False) -> List[Dict]:
        """
        查询所有仓库档案资料（自动翻页）

        Returns:
            仓库详情列表
        """
        debug_print = _get_debug_print()

        first_result = self.query(
            start_time=start_time,
            end_time=end_time,
            warehouse_no=warehouse_no,
            warehouse_name=warehouse_name,
            type=type,
            sub_type=sub_type,
            hide_delete=hide_delete,
            page_size=page_size,
            page_no=0,
            debug=debug,
        )

        if str(first_result.get('status')) != '0':
            if debug:
                msg = first_result.get('message') or first_result.get('code') or first_result
                debug_print(f"    [DEBUG] API错误: status={first_result.get('status')} {msg}")
            return []

        data = first_result.get('data', {})
        total_count = int(data.get('total_count', 0))
        first_details = data.get('details', [])

        if debug:
            debug_print(f"    [DEBUG] 总数: {total_count}, 第1页: {len(first_details)}条")

        if total_count == 0:
            return []

        total_pages = (total_count + page_size - 1) // page_size
        if total_pages <= 1:
            return first_details

        all_details = list(first_details)
        for page_no in range(1, total_pages):
            if debug:
                debug_print(f"    [DEBUG] 请求第 {page_no + 1}/{total_pages} 页...")
            result = self.query(
                start_time=start_time,
                end_time=end_time,
                warehouse_no=warehouse_no,
                warehouse_name=warehouse_name,
                type=type,
                sub_type=sub_type,
                hide_delete=hide_delete,
                page_size=page_size,
                page_no=page_no,
                debug=False,
            )
            if str(result.get('status')) == '0':
                all_details.extend(result.get('data', {}).get('details', []))

        if debug:
            debug_print(f"    [DEBUG] 共获取 {len(all_details)} 条")
        return all_details
