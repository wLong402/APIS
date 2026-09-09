# -*- coding: utf-8 -*-
"""
货品档案查询 API

goods.Goods.queryWithSpec - 获取ERP的货品档案资料（含单品规格）
文档: https://open.wangdian.cn/qjb/open/apidoc/doc?path=goods.Goods.queryWithSpec
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


class QueryGoodsWithSpecAPI:
    """
    货品档案查询 API

    支持按修改时间增量获取；start_time / end_time 最大跨度 30 天。
    API方法: goods.Goods.queryWithSpec

    响应:
        - status / message
        - data.total_count
        - data.goods_list[]（含嵌套 spec_list）
    """

    METHOD = 'goods.Goods.queryWithSpec'

    def __init__(self, client: Optional[OpenAPIClient] = None,
                 config: Optional[WdtConfig] = None,
                 gateway_url: Optional[str] = None):
        self.client = client or OpenAPIClient(config)
        if gateway_url:
            self.client.GATEWAY_URL = gateway_url

    def query(self,
              start_time: Optional[str] = None,
              end_time: Optional[str] = None,
              spec_no: Optional[str] = None,
              goods_no: Optional[str] = None,
              brand_name: Optional[str] = None,
              class_name: Optional[str] = None,
              barcode: Optional[str] = None,
              hide_deleted: int = 1,
              page_size: int = 200,
              page_no: int = 0,
              debug: bool = False) -> Dict:
        """
        查询货品档案（单页）

        Args:
            start_time / end_time: 货品或单品最后修改时间，最大跨度 30 天
            spec_no: 商家编码（不传时间时，spec_no 与 goods_no 须传其一）
            goods_no: 货品编号
            brand_name: 品牌名称
            class_name: 分类名称
            barcode: 条码
            hide_deleted: 0 返回全部；1 隐藏已删除（文档默认隐藏）
            page_no: 从 0 开始
        """
        params = {}
        if start_time:
            params['start_time'] = start_time
        if end_time:
            params['end_time'] = end_time
        if spec_no:
            params['spec_no'] = spec_no
        if goods_no:
            params['goods_no'] = goods_no
        if brand_name:
            params['brand_name'] = brand_name
        if class_name:
            params['class_name'] = class_name
        if barcode:
            params['barcode'] = barcode
        params['hide_deleted'] = hide_deleted

        pager = {'page_size': page_size, 'page_no': page_no, 'calc_total': 1}
        result = self.client.call(self.METHOD, params, pager, debug=debug)

        if debug:
            debug_print = _get_debug_print()
            status_code = result.get('status')
            data = result.get('data', {}) or {}
            total = data.get('total_count', 0)
            goods_list = data.get('goods_list', []) or []
            debug_print(
                f"    [DEBUG] API响应: status={status_code}, "
                f"total_count={total}, 本页={len(goods_list)}条"
            )

        return result

    def query_all(self,
                  start_time: Optional[str] = None,
                  end_time: Optional[str] = None,
                  spec_no: Optional[str] = None,
                  goods_no: Optional[str] = None,
                  brand_name: Optional[str] = None,
                  class_name: Optional[str] = None,
                  barcode: Optional[str] = None,
                  hide_deleted: int = 1,
                  page_size: int = 200,
                  debug: bool = False) -> List[Dict]:
        """查询全部货品（自动翻页），返回 goods_list。"""
        debug_print = _get_debug_print()

        first_result = self.query(
            start_time=start_time,
            end_time=end_time,
            spec_no=spec_no,
            goods_no=goods_no,
            brand_name=brand_name,
            class_name=class_name,
            barcode=barcode,
            hide_deleted=hide_deleted,
            page_size=page_size,
            page_no=0,
            debug=debug,
        )

        if str(first_result.get('status')) != '0':
            if debug:
                msg = first_result.get('message') or first_result.get('code') or first_result
                debug_print(f"    [DEBUG] API错误: status={first_result.get('status')} {msg}")
            return []

        data = first_result.get('data', {}) or {}
        total_count = int(data.get('total_count', 0) or 0)
        first_list = data.get('goods_list', []) or []

        if debug:
            debug_print(f"    [DEBUG] 总数: {total_count}, 第1页: {len(first_list)}条")

        if total_count == 0:
            return []

        total_pages = (total_count + page_size - 1) // page_size
        if total_pages <= 1:
            return first_list

        all_goods = list(first_list)
        for page_no in range(1, total_pages):
            if debug:
                debug_print(f"    [DEBUG] 请求第 {page_no + 1}/{total_pages} 页...")
            result = self.query(
                start_time=start_time,
                end_time=end_time,
                spec_no=spec_no,
                goods_no=goods_no,
                brand_name=brand_name,
                class_name=class_name,
                barcode=barcode,
                hide_deleted=hide_deleted,
                page_size=page_size,
                page_no=page_no,
                debug=False,
            )
            if str(result.get('status')) == '0':
                all_goods.extend((result.get('data', {}) or {}).get('goods_list', []) or [])

        if debug:
            debug_print(f"    [DEBUG] 共获取 {len(all_goods)} 条货品")
        return all_goods
