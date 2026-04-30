#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI 模块入口

支持使用 python -m cli 方式运行
"""

import sys
import os

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from cli.main import main

if __name__ == '__main__':
    sys.exit(main())

