# -*- coding: utf-8 -*-
"""
OperantID 任务模板 — 复制此文件到 operant/tasks/ 并修改后，在 operant/tasks/__init__.py 中 import。

步骤:
  1. 在 config.yaml 的 operantid.accounts 里配置登录帐号
  2. 写 build_mission(start, end, extras) 描述登录/筛选/下载步骤
  3. register_task(OperantTask(...))
"""

from operant.registry import register_task
from operant.task import OperantTask


def _build_mission(start: str, end: str, extras: dict) -> str:
    login_url = extras.get('login_url') or 'https://example.com/login'
    extra = extras.get('instruction') or ''
    return (
        f'打开 {login_url}，用提供的帐号登录。\n'
        f'进入数据导出页，筛选 {start} 到 {end}，下载 CSV 或 Excel。\n'
        f'{extra}\n'
        '完成后结束。不要在回复里写出密码。'
    )


# register_task(OperantTask(
#     name='example_export',
#     label='示例站点导出',
#     description='登录示例站点并按日期下载报表',
#     target_table='example_export',
#     unique_key='rowKey',
#     login_url='https://example.com/login',
#     account_name='example',
#     build_mission=_build_mission,
# ))
