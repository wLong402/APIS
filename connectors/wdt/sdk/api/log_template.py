# -*- coding: utf-8 -*-

from typing import Dict, Any


def summarize_value(value: Any, max_len: int = 120) -> str:
    if value is None:
        return "None"
    if isinstance(value, list):
        return f"<{len(value)} items>"
    if isinstance(value, dict):
        return f"<{len(value)} keys>"
    text = str(value)
    if len(text) > max_len:
        return text[:max_len] + f"...<{len(text)} chars>"
    return text


def summarize_params(params: Dict[str, Any], max_len: int = 120) -> str:
    parts = []
    for key in sorted(params.keys()):
        parts.append(f"{key}={summarize_value(params.get(key), max_len=max_len)}")
    return ", ".join(parts)


def summarize_response(resp_data: Dict[str, Any]) -> str:
    data_list = resp_data.get("data") if isinstance(resp_data, dict) else None
    data_count = len(data_list) if isinstance(data_list, list) else 0
    return (
        f"resultCode={resp_data.get('resultCode')}, "
        f"message={resp_data.get('message', '')}, "
        f"data_count={data_count}, "
        f"nextRequestId={resp_data.get('nextRequestId')}"
    )
