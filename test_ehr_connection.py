#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 EHR 数据库连接

用于诊断 SQL Server 连接问题
"""

import sys
import os

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.config import get_config
from connectors.weiban.utils.ehr_db import get_staff_ids_from_ehr


def test_connection():
    """测试 EHR 数据库连接"""
    print("\n" + "="*60)
    print("测试 EHR 数据库连接")
    print("="*60)
    
    try:
        config = get_config()
        weiban_config = config.get_connector_config('weiban') or {}
        ehr_config = weiban_config.get('ehr_database')
        
        if not ehr_config:
            print("\n[ERROR] 未配置 EHR 数据库")
            print("请在 config.yaml 中添加 weiban.ehr_database 配置")
            return False
        
        print(f"\n数据库配置:")
        print(f"  主机: {ehr_config.get('host')}")
        print(f"  端口: {ehr_config.get('port')}")
        print(f"  用户: {ehr_config.get('user')}")
        print(f"  数据库: {ehr_config.get('database')}")
        
        print(f"\n正在连接...")
        
        # 尝试连接并获取员工ID
        staff_ids = get_staff_ids_from_ehr(ehr_config)
        
        print(f"\n[OK] 连接成功！")
        print(f"  获取到 {len(staff_ids)} 个员工ID")
        
        if staff_ids:
            print(f"\n前10个员工ID:")
            for i, sid in enumerate(staff_ids[:10], 1):
                print(f"  {i}. {sid}")
            if len(staff_ids) > 10:
                print(f"  ... 还有 {len(staff_ids) - 10} 个")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 连接失败: {e}")
        print(f"\n可能的解决方案:")
        print(f"1. 检查网络连接是否正常")
        print(f"2. 确认服务器地址和端口正确")
        print(f"3. 检查防火墙设置")
        print(f"4. 确认 SQL Server 服务正在运行")
        print(f"5. 验证用户名和密码是否正确")
        print(f"6. 安装必要的库: pip install sqlalchemy pandas pymssql")
        return False


if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)

