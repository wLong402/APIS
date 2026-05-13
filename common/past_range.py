# -*- coding: utf-8 -*-

import calendar
from datetime import datetime, timedelta
from typing import Optional, Tuple

PAST_UNITS = ('second', 'minute', 'hour', 'day', 'week', 'month')

_UNIT_ALIASES = {
    's': 'second', 'sec': 'second', 'second': 'second', 'seconds': 'second', '秒': 'second',
    'm': 'minute', 'min': 'minute', 'minute': 'minute', 'minutes': 'minute', '分': 'minute', '分钟': 'minute',
    'h': 'hour', 'hr': 'hour', 'hour': 'hour', 'hours': 'hour', '时': 'hour', '小时': 'hour',
    'd': 'day', 'day': 'day', 'days': 'day', '天': 'day', '日': 'day',
    'w': 'week', 'week': 'week', 'weeks': 'week', '周': 'week', '星期': 'week',
    'mo': 'month', 'month': 'month', 'months': 'month', '月': 'month',
}


def normalize_past_unit(unit: Optional[str]) -> str:
    if not unit:
        return 'day'
    key = str(unit).strip().lower()
    u = _UNIT_ALIASES.get(key)
    if u:
        return u
    raise ValueError(f'不支持的回溯单位: {unit}，可选: {", ".join(PAST_UNITS)}')


def _subtract_months(dt: datetime, months: int) -> datetime:
    months = int(months)
    y = dt.year
    m = dt.month - months
    while m <= 0:
        m += 12
        y -= 1
    d = min(dt.day, calendar.monthrange(y, m)[1])
    return dt.replace(year=y, month=m, day=d)


def resolve_past_amount(payload: dict) -> Tuple[Optional[float], str]:
    amount = payload.get('past_value')
    if amount in (None, ''):
        amount = payload.get('past_days')
    if amount in (None, ''):
        return None, 'day'
    unit = normalize_past_unit(payload.get('past_unit') or 'day')
    return float(amount), unit


def compute_past_time_range(amount: float, unit: str) -> Tuple[str, str]:
    unit = normalize_past_unit(unit)
    now = datetime.now()
    amount = float(amount)
    if amount <= 0:
        raise ValueError('回溯数值必须大于 0')

    if unit == 'second':
        start = now - timedelta(seconds=amount)
    elif unit == 'minute':
        start = now - timedelta(minutes=amount)
    elif unit == 'hour':
        start = now - timedelta(hours=amount)
    elif unit == 'day':
        start = now - timedelta(days=amount)
        return start.strftime('%Y-%m-%d 00:00:00'), now.strftime('%Y-%m-%d 23:59:59')
    elif unit == 'week':
        start = now - timedelta(weeks=amount)
        return start.strftime('%Y-%m-%d 00:00:00'), now.strftime('%Y-%m-%d 23:59:59')
    elif unit == 'month':
        start = _subtract_months(now, int(amount))
        return start.strftime('%Y-%m-%d 00:00:00'), now.strftime('%Y-%m-%d 23:59:59')
    else:
        raise ValueError(f'不支持的回溯单位: {unit}')

    return start.strftime('%Y-%m-%d %H:%M:%S'), now.strftime('%Y-%m-%d %H:%M:%S')
