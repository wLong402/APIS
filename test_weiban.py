#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微伴连接器测试脚本

快速测试微伴连接器的功能
"""

import sys
import os

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from connectors.weiban.services import ExternalUserPullService
from connectors.weiban.client import get_weiban_client
from core.logger import get_logger

logger = get_logger('test.weiban')


def test_token():
    """测试 Token 获取"""
    print("\n" + "="*60)
    print("测试 1: Token 获取")
    print("="*60)
    
    try:
        client = get_weiban_client()
        token = client._api_client.get_access_token()
        print(f"[OK] Token 获取成功: {token[:20]}...")
        return True
    except Exception as e:
        print(f"[ERROR] Token 获取失败: {e}")
        return False


def test_api():
    """测试 API 调用"""
    print("\n" + "="*60)
    print("测试 2: API 调用")
    print("="*60)
    
    try:
        client = get_weiban_client()
        # 获取少量数据测试
        result = client.external_user_api.list(limit=5, debug=True)
        
        if result.get('errcode') == 0:
            users = result.get('external_user_list', [])
            total = result.get('total', 0)
            print(f"[OK] API 调用成功")
            print(f"  总数: {total}")
            print(f"  本次返回: {len(users)} 条")
            if users:
                print(f"  示例客户ID: {users[0].get('id')}")
            return True
        else:
            print(f"[ERROR] API 返回错误: {result.get('errmsg')}")
            return False
    except Exception as e:
        print(f"[ERROR] API 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pull_today():
    """测试拉取当前客户数据（实时接口）"""
    print("\n" + "="*60)
    print("测试 3: 拉取当前客户数据（实时接口）")
    print("="*60)
    
    try:
        service = ExternalUserPullService()
        result = service.pull_today(debug=True)
        
        print(f"\n[OK] 拉取完成")
        print(f"  获取: {result.fetched} 条")
        print(f"  保存: {result.saved} 条")
        print(f"  新加入: {result.details.get('new_joined', 0)} 条")
        print(f"  标记流失: {result.details.get('outflow_marked', 0)} 条")
        print(f"  耗时: {result.duration:.2f} 秒")
        
        return result.success
    except Exception as e:
        print(f"[ERROR] 拉取失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_statistics():
    """测试统计信息"""
    print("\n" + "="*60)
    print("测试 4: 统计信息")
    print("="*60)
    
    try:
        service = ExternalUserPullService()
        stats = service.get_statistics()
        
        print(f"[OK] 统计信息获取成功")
        print(f"  总客户数: {stats['total']}")
        print(f"  活跃客户: {stats['active']}")
        print(f"  已流失: {stats['outflow']}")
        
        return True
    except Exception as e:
        print(f"[ERROR] 统计失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("微伴连接器测试")
    print("="*60)
    
    results = []
    
    # 测试 1: Token 获取
    results.append(("Token 获取", test_token()))
    
    # 测试 2: API 调用
    results.append(("API 调用", test_api()))
    
    # 测试 3: 拉取数据（可选，需要数据库连接）
    # 在非交互式环境下跳过
    import sys
    if sys.stdin.isatty():
        print("\n是否测试数据拉取？(需要数据库连接) [y/N]: ", end='')
        try:
            choice = input().strip().lower()
            if choice == 'y':
                results.append(("数据拉取", test_pull_today()))
                results.append(("统计信息", test_statistics()))
        except (KeyboardInterrupt, EOFError):
            print("\n\n跳过数据拉取测试")
    else:
        print("\n非交互式环境，跳过数据拉取测试（需要数据库连接）")
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} - {name}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

