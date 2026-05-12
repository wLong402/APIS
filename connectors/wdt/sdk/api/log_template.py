# -*- coding: utf-8 -*-

from typing import Dict, Any, Optional


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


def summarize_response(
    resp_data: Dict[str, Any],
    *,
    api_params: Optional[Dict[str, Any]] = None,
    http_status: Optional[int] = None,
) -> str:
    data_list = resp_data.get("data") if isinstance(resp_data, dict) else None
    data_count = len(data_list) if isinstance(data_list, list) else 0
    sub_rc = resp_data.get("sub_resultCode") if isinstance(resp_data, dict) else None
    sub_de = resp_data.get("sub_detail") if isinstance(resp_data, dict) else None
    sub_part = ""
    if sub_rc not in (None, "", "None"):
        sub_part += f", sub_resultCode={sub_rc}"
    if sub_de not in (None, "", "None"):
        sub_part += f", sub_detail={summarize_value(sub_de, max_len=80)}"
    core = (
        f"resultCode={resp_data.get('resultCode')}, "
        f"message={resp_data.get('message', '')}, "
        f"data_count={data_count}, "
        f"nextRequestId={resp_data.get('nextRequestId')}"
        f"{sub_part}"
    )
    prefix = []
    if http_status is not None:
        prefix.append(f"http={http_status}")
    if api_params is not None:
        prefix.append(f"api_params={summarize_params(api_params)}")
    if prefix:
        return ", ".join(prefix) + ", " + core
    return core
