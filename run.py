#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据同步平台 - 新框架入口

使用方式:
    python run.py pull -c wdt -s trade                           # 拉取今日订单
    python run.py pull -c wdt -s trade --start 2025-12-01        # 指定日期
    python run.py pull -c wdt -s refund --interval 3600          # 按小时拉取退款单
    python run.py list                                           # 列出所有连接器
    python run.py stats                                          # 查看队列统计

注意：
    - 此文件是新框架的入口，与原有的 main.py 并存
    - 原有的 main.py 仍可正常使用
    - 新框架的数据表会有 wdt_ 前缀，与原表区分
"""

import sys
import os

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from cli.main import main

if __name__ == '__main__':
    sys.exit(main())

