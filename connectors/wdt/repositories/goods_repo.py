# -*- coding: utf-8 -*-

import json
from typing import List, Dict

from common.base_repository import BaseRepository
from .goods_spec_repo import GoodsSpecRepository


class GoodsRepository(BaseRepository):
    """
    货品档案主表；save_batch 时拆出 spec_list 写入 wdt_goods_spec。
    """

    TABLE_NAME = 'goods'
    UNIQUE_KEY = 'goods_id'
    SYSTEM_PREFIX = 'wdt'

    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.spec_repo = GoodsSpecRepository(db_manager)

    def save_batch(self, data_list: List[Dict], batch_size: int = 500,
                   debug: bool = False, progress_label: str = '', **kwargs) -> int:
        if not data_list:
            return 0

        goods_list = []
        spec_list = []

        self.logger.info(f"开始处理 {len(data_list)} 条货品，提取规格明细...")

        for goods in data_list:
            goods_id = goods.get('goods_id')
            nested = goods.get('spec_list') or []
            if isinstance(nested, str):
                try:
                    nested = json.loads(nested)
                except Exception:
                    nested = []

            if isinstance(nested, list) and goods_id is not None:
                for spec in nested:
                    if not isinstance(spec, dict):
                        continue
                    item = spec.copy()
                    item['goods_id'] = goods_id
                    # 嵌套数组落 JSON，避免拆第三层表
                    for key in ('barcode_list', 'img_more_url'):
                        val = item.get(key)
                        if isinstance(val, (list, dict)):
                            item[key] = json.dumps(val, ensure_ascii=False)
                    spec_list.append(item)

            goods_copy = goods.copy()
            if 'spec_list' in goods_copy:
                del goods_copy['spec_list']
            goods_list.append(goods_copy)

        self.logger.info(f"提取到 {len(spec_list)} 条规格，开始保存货品主表...")
        count = super().save_batch(
            goods_list, batch_size, debug=debug, progress_label=progress_label
        )

        if spec_list:
            self.logger.info(f"开始保存 {len(spec_list)} 条货品规格...")
            sub = f"{progress_label}.spec" if progress_label else ""
            self.spec_repo.save_batch(
                spec_list, batch_size, debug=debug, progress_label=sub
            )
            self.logger.info("保存货品规格完成")

        return count
