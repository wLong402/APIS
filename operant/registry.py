# -*- coding: utf-8 -*-

from typing import Dict, List, Optional

from .task import OperantTask

_TASKS: Dict[str, OperantTask] = {}


def register_task(task: OperantTask) -> OperantTask:
    if not task.name:
        raise ValueError('OperantTask.name 不能为空')
    _TASKS[task.name] = task
    return task


def get_task(name: str) -> Optional[OperantTask]:
    return _TASKS.get(name)


def list_tasks() -> List[OperantTask]:
    return sorted(_TASKS.values(), key=lambda t: t.name)


def task_options() -> List[dict]:
    return [
        {
            'name': t.name,
            'label': t.label,
            'description': t.description,
            'target_table': t.target_table,
            'unique_key': t.unique_key,
            'login_url': t.login_url,
            'account_name': t.account_name,
            'default_instruction': t.default_instruction,
        }
        for t in list_tasks()
    ]
