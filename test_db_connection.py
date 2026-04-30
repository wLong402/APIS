#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据库连接
"""
import sys
sys.path.append('.')

from core.config import get_config
from core.database import get_db_manager

def test_db_connection():
    """测试数据库连接"""
    try:
        # 加载配置
        config = get_config()
        print(f"数据库配置: {config.database.host}:{config.database.port}")
        print(f"数据库类型: {config.database.type}")

        # 获取数据库管理器
        db_manager = get_db_manager()

        # 执行简单查询
        with db_manager.get_connection() as conn:
            cursor = db_manager.adapter.get_cursor(conn)
            cursor.execute("SELECT 1 AS test")
            result = cursor.fetchone()
            print(f"数据库连接测试成功: {result}")

        # 获取连接池状态
        status = db_manager.pool_status
        print(f"连接池状态: {status}")

        return True

    except Exception as e:
        print(f"数据库连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_db_connection()
    sys.exit(0 if success else 1)