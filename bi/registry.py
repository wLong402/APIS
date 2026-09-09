# -*- coding: utf-8 -*-

from typing import Dict, List, Optional

from .task import BiTask

_TASKS: Dict[str, BiTask] = {}


def register_task(task: BiTask) -> BiTask:
    if not task.name:
        raise ValueError('BiTask.name 不能为空')
    _TASKS[task.name] = task
    return task


def get_task(name: str) -> Optional[BiTask]:
    return _TASKS.get(name)


def list_tasks() -> List[BiTask]:
    return sorted(_TASKS.values(), key=lambda t: t.name)


def task_options() -> List[dict]:
    return [
        {
            'name': t.name,
            'label': t.label,
            'description': t.description,
            'target_table': t.target_table,
            'target_database': t.target_database,
            'date_column': t.date_column,
        }
        for t in list_tasks()
    ]
