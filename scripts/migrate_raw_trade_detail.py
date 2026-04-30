# -*- coding: utf-8 -*-
"""
迁移脚本：将 rawtrade 表中的 trade_orders 字段解析存到 raw_trade_detail 表

使用方法:
    python scripts/migrate_raw_trade_detail.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db_manager
from core.logger import get_logger
from connectors.wdt.repositories.raw_trade_detail_repo import RawTradeDetailRepository
from core.database import sanitize_column_name

logger = get_logger('migrate_raw_trade_detail')


def migrate_trade_orders():
    """迁移 trade_orders 字段到明细表"""
    db = get_db_manager()
    detail_repo = RawTradeDetailRepository(db)
    
    source_table = 'wdt_raw_trade'
    target_table = detail_repo.full_table_name
    
    logger.info(f"开始迁移: {source_table}.trade_orders -> {target_table}")
    
    # 检查源表是否存在
    if not db.table_exists(source_table):
        logger.error(f"源表 {source_table} 不存在")
        return
    
    # 检查目标表是否存在，不存在则创建
    if not db.table_exists(target_table):
        logger.info(f"目标表 {target_table} 不存在，将在保存时自动创建")
    
    # 查询所有有 trade_orders 的记录
    sql = f"""
        SELECT `trade_orders` 
        FROM `{source_table}` 
        WHERE `trade_orders` IS NOT NULL 
        AND `trade_orders` != ''
        AND `trade_orders` != '[]'
    """
    
    logger.info("查询源表数据...")
    trades = db.fetch_all(sql)
    total_trades = len(trades)
    
    if total_trades == 0:
        logger.info("没有需要迁移的数据")
        return
    
    logger.info(f"找到 {total_trades} 条订单需要处理")
    
    total_details = 0
    success_count = 0
    error_count = 0
    
    batch_size = 500
    detail_batch = []
    
    for idx, trade in enumerate(trades, 1):
        trade_orders_field = trade.get('trade_orders')
        
        if not trade_orders_field:
            continue
        
        # 解析 trade_orders 字段
        try:
            if isinstance(trade_orders_field, str):
                trade_orders = json.loads(trade_orders_field)
            elif isinstance(trade_orders_field, list):
                trade_orders = trade_orders_field
            else:
                logger.warning(f"第 {idx} 条记录的 trade_orders 格式异常: {type(trade_orders_field)}")
                continue
        except json.JSONDecodeError as e:
            logger.warning(f"第 {idx} 条记录的 trade_orders JSON 解析失败: {e}")
            continue
        
        if not isinstance(trade_orders, list):
            logger.warning(f"订单 {rec_id} 的 trade_orders 不是列表: {type(trade_orders)}")
            continue
        
        # 提取明细
        for order in trade_orders:
            if not isinstance(order, dict):
                continue
            
            detail_item = order.copy()
            detail_batch.append(detail_item)
            total_details += 1
        
        # 批量保存
        if len(detail_batch) >= batch_size:
            try:
                saved = detail_repo.save_batch(detail_batch, batch_size)
                success_count += saved
                logger.info(f"进度: {idx}/{total_trades} | 已保存明细: {success_count} 条")
                detail_batch = []
            except Exception as e:
                logger.error(f"批量保存失败: {e}", exc_info=True)
                error_count += len(detail_batch)
                detail_batch = []
        
        if idx % 100 == 0:
            logger.info(f"进度: {idx}/{total_trades} | 已处理明细: {total_details} 条")
    
    # 保存剩余的明细
    if detail_batch:
        try:
            saved = detail_repo.save_batch(detail_batch, batch_size)
            success_count += saved
        except Exception as e:
            logger.error(f"批量保存失败: {e}", exc_info=True)
            error_count += len(detail_batch)
    
    logger.info("=" * 60)
    logger.info("迁移完成")
    logger.info(f"处理订单数: {total_trades}")
    logger.info(f"提取明细数: {total_details}")
    logger.info(f"成功保存: {success_count} 条")
    logger.info(f"失败: {error_count} 条")
    logger.info("=" * 60)


if __name__ == '__main__':
    try:
        migrate_trade_orders()
    except Exception as e:
        logger.error(f"迁移失败: {e}", exc_info=True)
        sys.exit(1)

