# -*- coding: utf-8 -*-
"""跑 OperantID 浏览器任务：登录 → 下载 → 入库。"""

import asyncio
import os
import shutil
import time
from datetime import datetime, timedelta
from typing import Optional

from common.past_range import compute_past_time_range, resolve_past_amount
from core.logger import get_logger

from .client import get_account, load_operant_config, require_operantid
from .ingest import (
    attach_row_keys,
    ingest_files,
    list_data_files,
    parse_result_message,
    sanitize_table_name,
)
from .registry import get_task

logger = get_logger('operant')


def resolve_date_range(
    start: Optional[str] = None,
    end: Optional[str] = None,
    past_value=None,
    past_unit: Optional[str] = None,
    past_days=None,
) -> tuple:
    amount, unit = resolve_past_amount({
        'past_value': past_value,
        'past_days': past_days,
        'past_unit': past_unit,
    })
    if amount is not None:
        start_time, end_time = compute_past_time_range(amount, unit)
        return start_time.split(' ')[0], end_time.split(' ')[0]
    today = datetime.now().strftime('%Y-%m-%d')
    s = (start or today).split(' ')[0]
    e = (end or start or today).split(' ')[0]
    return s, e


def _abs_download_dir(base: str, job_tag: str) -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = base if os.path.isabs(base) else os.path.join(root, base, job_tag)
    os.makedirs(path, exist_ok=True)
    return path


def _on_step(data: dict) -> None:
    step = data.get('step')
    reasoning = (data.get('reasoning') or '').strip()
    action = data.get('action') or {}
    action_type = action.get('type') or ''
    text = action.get('text') or action.get('selector') or ''
    line = f'    [STEP {step}] {action_type} {text}'.rstrip()
    if reasoning:
        line += f' | {reasoning[:160]}'
    print(line, flush=True)


async def _execute_agent(agent, mission: str):
    return await agent.execute(mission, on_step=_on_step)


def run_operant_task(
    task_name: str,
    account: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    past_value=None,
    past_unit: Optional[str] = None,
    past_days=None,
    instruction: Optional[str] = None,
    login_url: Optional[str] = None,
    target_table: Optional[str] = None,
    unique_key: Optional[str] = None,
    headless: Optional[bool] = None,
    debug: bool = False,
) -> int:
    import operant.tasks  # noqa: F401

    task = get_task(task_name)
    if not task:
        raise ValueError(f'未知 OperantID 任务: {task_name}')

    conf = load_operant_config()
    if not conf.get('enabled', True):
        raise RuntimeError('config.yaml 中 operantid.enabled=false，已关闭实验功能')
    if not conf.get('api_key'):
        raise RuntimeError('未配置 OperantID API Key（operantid.api_key 或环境变量 OPERANTID_API_KEY）')

    if (
        task.default_yesterday
        and not start and not end
        and past_value in (None, '')
        and past_days in (None, '')
    ):
        yday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        start_date, end_date = yday, yday
    else:
        start_date, end_date = resolve_date_range(start, end, past_value, past_unit, past_days)
    acc_name = account or task.account_name
    acc = get_account(acc_name) if acc_name else None
    extras = {
        'account': acc_name,
        'login_url': login_url or (acc or {}).get('login_url') or task.login_url,
        'instruction': instruction or task.default_instruction,
        'save_as': task.save_as,
        'download_dir': task.download_dir,
    }
    mission = task.mission(start_date, end_date, extras)
    table = sanitize_table_name(target_table or task.target_table)
    uk = unique_key or task.unique_key or 'rowKey'
    job_tag = f'{task_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    if task.download_dir:
        download_dir = task.download_dir
        if not os.path.isabs(download_dir):
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            download_dir = os.path.join(root, download_dir)
        os.makedirs(download_dir, exist_ok=True)
    else:
        download_dir = _abs_download_dir(conf['download_dir'], job_tag)
    save_as_path = ''
    if task.save_as:
        save_as_path = task.save_as if os.path.isabs(task.save_as) else os.path.join(download_dir, task.save_as)
        os.makedirs(os.path.dirname(save_as_path) or download_dir, exist_ok=True)

    print('=' * 60, flush=True)
    print('OperantID 实验任务', flush=True)
    print('=' * 60, flush=True)
    print(f'任务:   {task.name} ({task.label})', flush=True)
    print(f'帐号:   {acc_name or "（未指定，仅在任务指令里登录）"}', flush=True)
    print(f'时间:   {start_date} ~ {end_date}', flush=True)
    print(f'落库:   operant_{table}  UK={uk}', flush=True)
    print(f'下载目录: {download_dir}', flush=True)
    if save_as_path:
        print(f'保存为: {save_as_path}', flush=True)
    print(f'headless: {conf["headless"] if headless is None else bool(headless)}', flush=True)
    print('=' * 60, flush=True)
    if debug:
        print(f'[DEBUG] mission:\n{mission}\n', flush=True)

    Agent = require_operantid()
    browser_config = dict(conf.get('browser_config') or {})
    browser_config.setdefault('locale', 'zh-CN')
    browser_config.setdefault('timezone', 'Asia/Shanghai')
    browser_config['downloads_path'] = download_dir
    browser_config['accept_downloads'] = True

    agent_kwargs = {
        'api_key': conf['api_key'],
        'provider': conf['provider'],
        'model': conf['model'],
        'headless': conf['headless'] if headless is None else bool(headless),
        'browser_config': browser_config,
    }
    if conf.get('base_url'):
        agent_kwargs['base_url'] = conf['base_url']
    if acc:
        agent_kwargs['email'] = acc.get('email') or ''
        agent_kwargs['password'] = acc.get('password') or ''

    before = set(list_data_files(download_dir))
    started = time.time()
    agent = Agent(**agent_kwargs)
    if hasattr(agent, 'max_steps'):
        agent.max_steps = task.max_steps or conf['max_steps']

    try:
        result = asyncio.run(_execute_agent(agent, mission))
    finally:
        closer = getattr(agent, 'close', None) or getattr(agent, 'stop', None)
        if callable(closer):
            try:
                maybe = closer()
                if asyncio.iscoroutine(maybe):
                    asyncio.run(maybe)
            except Exception:
                pass

    if not isinstance(result, dict):
        result = {'success': bool(result), 'message': str(result or '')}
    ok = bool(result.get('success', True))
    message = result.get('message') or ''
    steps = result.get('steps')
    print(f'    [AGENT] success={ok} steps={steps} elapsed={time.time() - started:.1f}s', flush=True)
    if message:
        preview = message if len(str(message)) < 400 else str(message)[:400] + '...'
        print(f'    [AGENT] message={preview}', flush=True)
    if not ok:
        raise RuntimeError(message or 'OperantID 任务失败')

    after = list_data_files(download_dir)
    new_files = [p for p in after if p not in before] or after
    if save_as_path and new_files:
        src = new_files[-1]
        if os.path.abspath(src) != os.path.abspath(save_as_path):
            if os.path.exists(save_as_path):
                os.remove(save_as_path)
            shutil.copy2(src, save_as_path)
            print(f'    [SAVE] {src} -> {save_as_path}', flush=True)
        new_files = [save_as_path]
    saved = 0
    if new_files:
        saved = ingest_files(new_files, table, unique_key=uk, debug=debug)
    if saved == 0:
        rows = attach_row_keys(parse_result_message(message), uk)
        if rows:
            from .ingest import OperantDownloadRepository
            repo = OperantDownloadRepository(table, unique_key=uk if any(r.get(uk) for r in rows) else 'rowKey')
            saved = repo.save_batch(rows, debug=debug, progress_label=f'operant.{repo.full_table_name}')
            print(f'    [INGEST] 从 Agent 返回解析 {len(rows)} 行', flush=True)
    if saved == 0:
        print('    [WARN] 未发现可入库文件，也未从 Agent 返回解析到表格数据', flush=True)
        logger.warning('OperantID 任务 %s 无入库数据', task_name)
    else:
        print(f'    [OK] 写入 {saved} 行 -> operant_{table}', flush=True)
    return saved
