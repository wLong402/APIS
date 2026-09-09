# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class OperantTask:
    """
    OperantID 浏览器登录下载任务。

    新增任务：在 operant/tasks/ 下建模块，调用 register_task() 即可。
    build_mission(start, end, extras) 返回给 Agent 的自然语言指令。
    extras 含 account / login_url / instruction 等运行时覆盖项。
    """

    name: str
    label: str
    description: str
    target_table: str
    unique_key: str = 'rowKey'
    login_url: str = ''
    account_name: str = ''
    default_instruction: str = ''
    download_dir: str = ''
    save_as: str = ''
    default_yesterday: bool = False
    max_steps: int = 0
    build_mission: Optional[Callable[[str, str, dict], str]] = None

    def mission(self, start: str, end: str, extras: Optional[dict] = None) -> str:
        extras = extras or {}
        if self.build_mission:
            return self.build_mission(start, end, extras)
        login_url = extras.get('login_url') or self.login_url
        extra = extras.get('instruction') or self.default_instruction
        parts = [
            '用提供的帐号登录网站，按日期范围下载业务数据文件（优先 CSV / Excel / JSON）。',
            f'登录地址: {login_url}' if login_url else '',
            f'日期范围: {start} ~ {end}' if start or end else '',
            extra,
            '下载完成后结束任务。不要在回复里写出密码或完整帐号。',
        ]
        return '\n'.join(p for p in parts if p)
