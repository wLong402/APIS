# -*- coding: utf-8 -*-
"""定时任务调度

支持的触发模式：
    - daily: 每天 HH:MM
    - interval: 每 N 秒
    - cron: 简化版 "分 时 日 月 周"（* / 数字 / 逗号分隔）
"""

import os
import json
import time
import uuid
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from . import jobs as jobs_mod

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'web', 'data')
SCHED_FILE = os.path.join(DATA_DIR, 'schedules.json')
os.makedirs(DATA_DIR, exist_ok=True)

_lock = threading.Lock()
_schedules: List[dict] = []
_thread: Optional[threading.Thread] = None
_stop_evt = threading.Event()


def _load():
    global _schedules
    if os.path.exists(SCHED_FILE):
        try:
            with open(SCHED_FILE, 'r', encoding='utf-8') as f:
                _schedules = json.load(f)
        except Exception:
            _schedules = []
    else:
        _schedules = []


def _save():
    try:
        with open(SCHED_FILE, 'w', encoding='utf-8') as f:
            json.dump(_schedules, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_load()


def _parse_cron_field(expr: str, lo: int, hi: int) -> set:
    out = set()
    for part in str(expr).split(','):
        part = part.strip()
        if not part:
            continue
        if part == '*':
            return set(range(lo, hi + 1))
        if '/' in part:
            base, step = part.split('/', 1)
            step = int(step)
            if base == '*':
                rng = range(lo, hi + 1, step)
            else:
                rng = range(int(base), hi + 1, step)
            out.update(rng)
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            out.update(range(int(a), int(b) + 1))
            continue
        out.add(int(part))
    return out


def _match_cron(expr: str, now: datetime) -> bool:
    parts = expr.split()
    if len(parts) != 5:
        return False
    m, h, dom, mon, dow = parts
    try:
        if now.minute not in _parse_cron_field(m, 0, 59):
            return False
        if now.hour not in _parse_cron_field(h, 0, 23):
            return False
        if now.day not in _parse_cron_field(dom, 1, 31):
            return False
        if now.month not in _parse_cron_field(mon, 1, 12):
            return False
        if now.weekday() not in _parse_cron_field(dow, 0, 6):
            return False
    except Exception:
        return False
    return True


def _next_run(sched: dict, now: datetime) -> Optional[datetime]:
    trig = sched.get('trigger', {})
    t = trig.get('type')
    if t == 'daily':
        h, m = map(int, trig.get('time', '00:00').split(':'))
        nxt = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if nxt <= now:
            nxt += timedelta(days=1)
        return nxt
    if t == 'interval':
        secs = int(trig.get('seconds', 3600))
        return now + timedelta(seconds=secs)
    if t == 'cron':
        for i in range(1, 60 * 24 * 7 + 1):
            cand = (now + timedelta(minutes=i)).replace(second=0, microsecond=0)
            if _match_cron(trig.get('expr', ''), cand):
                return cand
        return None
    return None


def _scheduler_loop():
    while not _stop_evt.is_set():
        try:
            now = datetime.now().replace(second=0, microsecond=0)
            with _lock:
                items = list(_schedules)
            for s in items:
                if not s.get('enabled', True):
                    continue
                trig = s.get('trigger', {})
                t = trig.get('type')
                fire = False
                if t == 'daily':
                    h, m = map(int, trig.get('time', '00:00').split(':'))
                    if now.hour == h and now.minute == m:
                        fire = True
                elif t == 'cron':
                    if _match_cron(trig.get('expr', ''), now):
                        fire = True
                elif t == 'interval':
                    last = s.get('last_run_at')
                    secs = int(trig.get('seconds', 3600))
                    if not last:
                        fire = True
                    else:
                        last_dt = datetime.strptime(last, '%Y-%m-%d %H:%M:%S')
                        if (datetime.now() - last_dt).total_seconds() >= secs:
                            fire = True
                if fire:
                    last = s.get('last_run_at')
                    if t in ('daily', 'cron') and last:
                        last_dt = datetime.strptime(last, '%Y-%m-%d %H:%M:%S')
                        if last_dt.replace(second=0, microsecond=0) == now:
                            continue
                    try:
                        job = jobs_mod.run_job(s.get('payload', {}), source='schedule', schedule_id=s['id'])
                        with _lock:
                            for ss in _schedules:
                                if ss['id'] == s['id']:
                                    ss['last_run_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    ss['last_job_id'] = job['id']
                                    ss['next_run_at'] = _format_dt(_next_run(ss, datetime.now()))
                                    break
                            _save()
                    except Exception:
                        pass
        except Exception:
            pass
        _stop_evt.wait(20)


def _format_dt(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else None


def start():
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_evt.clear()
    _thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _thread.start()


def stop():
    _stop_evt.set()


def list_schedules() -> List[dict]:
    with _lock:
        out = []
        for s in _schedules:
            ss = dict(s)
            ss['next_run_at'] = _format_dt(_next_run(s, datetime.now()))
            out.append(ss)
        return out


def add_schedule(name: str, payload: dict, trigger: dict, enabled: bool = True) -> dict:
    sid = uuid.uuid4().hex[:10]
    s = {
        'id': sid,
        'name': name or f'{payload.get("connector")}.{payload.get("service")}',
        'payload': payload,
        'trigger': trigger,
        'enabled': enabled,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_run_at': None,
        'last_job_id': None,
    }
    with _lock:
        _schedules.append(s)
        _save()
    return s


def update_schedule(sid: str, **fields) -> Optional[dict]:
    with _lock:
        for s in _schedules:
            if s['id'] == sid:
                for k, v in fields.items():
                    if k in ('name', 'payload', 'trigger', 'enabled'):
                        s[k] = v
                _save()
                return s
    return None


def delete_schedule(sid: str) -> bool:
    with _lock:
        before = len(_schedules)
        _schedules[:] = [s for s in _schedules if s['id'] != sid]
        if len(_schedules) != before:
            _save()
            return True
    return False


def toggle_schedule(sid: str) -> Optional[dict]:
    with _lock:
        for s in _schedules:
            if s['id'] == sid:
                s['enabled'] = not s.get('enabled', True)
                _save()
                return s
    return None


def run_now(sid: str) -> Optional[dict]:
    with _lock:
        target = next((s for s in _schedules if s['id'] == sid), None)
    if not target:
        return None
    job = jobs_mod.run_job(target.get('payload', {}), source='schedule_manual', schedule_id=sid)
    with _lock:
        for s in _schedules:
            if s['id'] == sid:
                s['last_run_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                s['last_job_id'] = job['id']
                _save()
                break
    return job
