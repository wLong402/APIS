# -*- coding: utf-8 -*-
"""任务执行与记录"""

import os
import sys
import json
import time
import uuid
import signal
import threading
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'web', 'data')
LOGS_DIR = os.path.join(DATA_DIR, 'job_logs')
JOBS_FILE = os.path.join(DATA_DIR, 'jobs.json')

os.makedirs(LOGS_DIR, exist_ok=True)

_lock = threading.Lock()
_jobs: Dict[str, dict] = {}
_processes: Dict[str, subprocess.Popen] = {}
MAX_HISTORY = 200


def _load():
    global _jobs
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                _jobs = json.load(f)
        except Exception:
            _jobs = {}


def _save():
    try:
        items = sorted(_jobs.values(), key=lambda x: x.get('started_at', ''), reverse=True)
        if len(items) > MAX_HISTORY:
            for old in items[MAX_HISTORY:]:
                _jobs.pop(old['id'], None)
                lp = old.get('log_path')
                if lp and os.path.exists(lp):
                    try:
                        os.remove(lp)
                    except Exception:
                        pass
        with open(JOBS_FILE, 'w', encoding='utf-8') as f:
            json.dump(_jobs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_load()


def _resolve_python() -> str:
    """允许通过环境变量 DATA_SYNC_PYTHON 指定子进程使用的 python，否则用当前解释器"""
    return os.environ.get('DATA_SYNC_PYTHON') or sys.executable


def build_command(payload: dict) -> List[str]:
    """根据前端参数构建 run.py pull 命令行"""
    cmd = [_resolve_python(), '-u', os.path.join(ROOT, 'run.py'), 'pull',
           '-c', payload['connector'], '-s', payload['service']]

    mapping = {
        'start': '--start',
        'end': '--end',
        'past_days': '--past-days',
        'interval': '--interval',
        'shop_no': '--shop-no',
        'page_size': '--page-size',
        'workers': '--workers',
        'classification_name': '--classification-name',
        'start_config_record_time': '--start-config-record-time',
        'end_config_record_time': '--end-config-record-time',
        'is_summary': '--is-summary',
        'staff_ids': '--staff-ids',
        'scheme_name': '--scheme-name',
        'terms_income': '--terms-income',
        'composite_dim': '--composite-dim',
        'split_suite': '--split-suite',
        'cost_type': '--cost-type',
        'stat_mode': '--stat-mode',
        'order_way': '--order-way',
        'display_by_shop': '--display-by-shop',
        'display_by_date': '--display-by-date',
        'original_order': '--original-order',
        'plat_order_nos': '--plat-order-nos',
        'erp_order_nos': '--erp-order-nos',
        'shop_nos': '--shop-nos',
        'spec_no': '--spec-no',
        'project': '--project',
        'summary_no': '--summary-no',
        'expense_item_name': '--expense-item-name',
        'warehouse_no': '--warehouse-no',
    }
    for k, flag in mapping.items():
        v = payload.get(k)
        if v in (None, '', False):
            continue
        cmd.extend([flag, str(v)])

    if payload.get('by_day'):
        cmd.append('--by-day')
    if payload.get('debug'):
        cmd.append('--debug')
    if payload.get('no_ehr'):
        cmd.append('--no-ehr')
    return cmd


def run_job(payload: dict, source: str = 'manual', schedule_id: Optional[str] = None) -> dict:
    """启动一个拉取任务（异步）"""
    job_id = uuid.uuid4().hex[:12]
    cmd = build_command(payload)
    log_path = os.path.join(LOGS_DIR, f'{job_id}.log')

    job = {
        'id': job_id,
        'source': source,
        'schedule_id': schedule_id,
        'connector': payload.get('connector'),
        'service': payload.get('service'),
        'payload': payload,
        'cmd': ' '.join(cmd),
        'status': 'running',
        'exit_code': None,
        'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'finished_at': None,
        'log_path': log_path,
    }

    with _lock:
        _jobs[job_id] = job
        _save()

    def _runner():
        try:
            with open(log_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(f'$ {job["cmd"]}\n\n')
                f.flush()
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                creationflags = 0
                if os.name == 'nt':
                    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
                proc = subprocess.Popen(
                    cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT,
                    env=env, creationflags=creationflags,
                )
                _processes[job_id] = proc
                proc.wait()
                exit_code = proc.returncode
        except Exception as e:
            exit_code = -1
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(f'\n[ERROR] {e}\n')
            except Exception:
                pass
        finally:
            _processes.pop(job_id, None)
            with _lock:
                j = _jobs.get(job_id)
                if j:
                    j['exit_code'] = exit_code
                    if exit_code == 0:
                        j['status'] = 'success'
                    elif exit_code == 1:
                        j['status'] = 'warning'
                    elif exit_code in (-15, 15, 130, 143, -1073741510, 3221225786):
                        j['status'] = 'stopped'
                    else:
                        j['status'] = 'failed'
                    j['finished_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    _save()

    threading.Thread(target=_runner, daemon=True).start()
    return job


def stop_job(job_id: str) -> bool:
    proc = _processes.get(job_id)
    if not proc:
        return False
    try:
        if os.name == 'nt':
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            time.sleep(1)
            if proc.poll() is None:
                proc.terminate()
        else:
            proc.terminate()
        return True
    except Exception:
        try:
            proc.kill()
            return True
        except Exception:
            return False


def list_jobs(limit: int = 100) -> List[dict]:
    with _lock:
        items = list(_jobs.values())
    items.sort(key=lambda x: x.get('started_at', ''), reverse=True)
    return items[:limit]


def get_job(job_id: str) -> Optional[dict]:
    return _jobs.get(job_id)


import re as _re

_INFO_RE = _re.compile(r'\[(API )?DEBUG\]|\[INFO\]')
_ERR_RES = [
    _re.compile(r'\[ERROR\]'),
    _re.compile(r'\bERROR\b'),
    _re.compile(r'\bException\b'),
    _re.compile(r'\bTraceback\b'),
    _re.compile(r'拉取失败|\[数据不匹配\]|数据总数不匹配'),
    _re.compile(r'请求异常|请求失败|连接失败|连接超时|请求超时|读取超时'),
    _re.compile(r'HTTP状态码:\s*[45]\d\d'),
    _re.compile(r'表结构初始化失败|批量保存失败'),
]
_WARN_RES = [
    _re.compile(r'\[WARNING\]'),
    _re.compile(r'\bWARN(ING)?\b'),
    _re.compile(r'\[空页|⚠|返回空数据|数据为空|冲突'),
]
_FETCH_SAVE_RE = _re.compile(r'获取\s*(\d+)\s*条[，,]\s*保存\s*(\d+)\s*条')
_SUMMARY_ERR_RE = _re.compile(r'错误:\s*(\d+)\s*条')


def _classify_line(s: str) -> str:
    if _INFO_RE.search(s):
        return ''
    for r in _ERR_RES:
        if r.search(s):
            return 'err'
    for r in _WARN_RES:
        if r.search(s):
            return 'warn'
    m = _FETCH_SAVE_RE.search(s)
    if m:
        fetched, saved = int(m.group(1)), int(m.group(2))
        if fetched > 0 and saved < fetched:
            return 'err' if saved == 0 else 'warn'
    m = _SUMMARY_ERR_RE.search(s)
    if m and int(m.group(1)) > 0:
        return 'err'
    return ''


def summarize_log(job_id: str, tail_lines: int = 5000) -> dict:
    job = _jobs.get(job_id)
    if not job or not os.path.exists(job.get('log_path') or ''):
        return {'errors': [], 'warnings': [], 'totals': {}}
    try:
        with open(job['log_path'], 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()[-tail_lines:]
    except Exception:
        return {'errors': [], 'warnings': [], 'totals': {}}
    errors, warnings = [], []
    for i, ln in enumerate(lines):
        s = ln.rstrip('\n')
        kind = _classify_line(s)
        if kind == 'err':
            errors.append({'line': i + 1, 'text': s[:500]})
        elif kind == 'warn':
            warnings.append({'line': i + 1, 'text': s[:500]})
    return {
        'errors': errors[-50:],
        'warnings': warnings[-50:],
        'totals': {'error_count': len(errors), 'warning_count': len(warnings)},
    }


def read_log(job_id: str, offset: int = 0, max_bytes: int = 200_000) -> dict:
    job = _jobs.get(job_id)
    if not job:
        return {'content': '', 'offset': 0, 'eof': True}
    log_path = job.get('log_path')
    if not log_path or not os.path.exists(log_path):
        return {'content': '', 'offset': 0, 'eof': job.get('status') != 'running'}
    size = os.path.getsize(log_path)
    if offset >= size:
        return {'content': '', 'offset': size, 'eof': job.get('status') != 'running'}
    with open(log_path, 'rb') as f:
        f.seek(offset)
        chunk = f.read(max_bytes)
    try:
        text = chunk.decode('utf-8', errors='replace')
    except Exception:
        text = ''
    return {
        'content': text,
        'offset': offset + len(chunk),
        'eof': (offset + len(chunk) >= size) and (job.get('status') != 'running'),
    }
