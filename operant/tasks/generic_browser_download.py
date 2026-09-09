# -*- coding: utf-8 -*-
"""通用浏览器登录下载（实验）。登录地址 / 指令 / 目标表可在任务中心覆盖。"""

from operant.registry import register_task
from operant.task import OperantTask


def _build_mission(start: str, end: str, extras: dict) -> str:
    login_url = extras.get('login_url') or ''
    extra = extras.get('instruction') or ''
    if not login_url and not extra:
        raise ValueError('generic_browser_download 需要登录地址或下载指令')
    parts = [
        '这是一次浏览器数据下载任务。',
        f'打开 {login_url} 并用提供的帐号登录。' if login_url else '用提供的帐号登录当前任务指定的网站。',
        f'按日期范围 {start} ~ {end} 筛选数据。' if start or end else '',
        extra,
        '优先下载 CSV / Excel / JSON 文件。如果页面只有表格、没有导出按钮，把表格整理成 JSON 数组作为最终结果。',
        '完成后结束任务。不要在回复里写出密码或完整帐号。',
    ]
    return '\n'.join(p for p in parts if p)


register_task(OperantTask(
    name='generic_browser_download',
    label='通用浏览器下载',
    description='实验：用 OperantID 登录指定网站，按日期下载文件并写入 operant_* 表',
    target_table='browser_download',
    unique_key='rowKey',
    build_mission=_build_mission,
))
