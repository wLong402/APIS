# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime
from typing import Optional, Tuple

from common.past_range import compute_past_time_range, resolve_past_amount
from core.database import get_db_manager
from core.logger import DATE_FORMAT, LOG_FORMAT, get_logger

from .registry import get_task

logger = get_logger('bi.runner')


def resolve_bi_date_range(
    start: Optional[str] = None,
    end: Optional[str] = None,
    past_value=None,
    past_unit: Optional[str] = None,
    past_days: Optional[int] = None,
) -> Tuple[str, str]:
    """解析 BI 任务日期区间（闭区间，YYYY-MM-DD）。"""
    payload = {
        'past_value': past_value,
        'past_unit': past_unit,
        'past_days': past_days,
    }
    past_amount, unit = resolve_past_amount(payload)
    if past_amount is not None:
        start_time, end_time = compute_past_time_range(past_amount, unit)
        return start_time.split(' ')[0], end_time.split(' ')[0]

    today = datetime.now().strftime('%Y-%m-%d')
    start_date = (start or today).split(' ')[0][:10]
    end_date = (end or start or today).split(' ')[0][:10]
    return start_date, end_date


def _ensure_console_log() -> None:
    for h in logger.handlers:
        if getattr(h, '_bi_console', False):
            return
    sh = logging.StreamHandler()
    sh._bi_console = True
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(sh)


def _target_table_ref(task) -> str:
    if task.target_database:
        return f'[{task.target_database}].dbo.[{task.target_table}]'
    return f'dbo.[{task.target_table}]'


def _ensure_table(db, task) -> None:
    table_ref = _target_table_ref(task)
    row = db.fetch_one(f"SELECT CASE WHEN OBJECT_ID(N'{table_ref.replace('[', '').replace(']', '')}', N'U') IS NULL THEN 0 ELSE 1 END AS n")
    if row and int(list(row.values())[0]) > 0:
        return
    logger.info('创建 BI 结果表: %s', table_ref)
    db.execute(task.create_table_sql.strip())
    logger.info('BI 结果表已创建: %s', table_ref)


def _target_has_rows(db, task) -> bool:
    """仅判断目标表是否有数据（避免大表 COUNT 卡死）。"""
    row = db.fetch_one(f'SELECT TOP 1 1 AS n FROM {_target_table_ref(task)}')
    return bool(row)


def _build_insert_sql(table_ref: str, select_sql: str) -> str:
    """SQL Server: WITH 必须写在 INSERT 之前。"""
    s = select_sql.strip().rstrip(';')
    if not s.upper().startswith('WITH'):
        return f"INSERT INTO {table_ref}\n{s}"
    pos = -1
    for m in re.finditer(r'\nSELECT\r?\n', s, flags=re.IGNORECASE):
        line_start = m.start() + 1
        if line_start < len(s) and s[line_start] not in ' \t':
            pos = line_start
    if pos < 0:
        raise ValueError('CTE 查询未找到主 SELECT，无法生成 INSERT')
    return f"{s[:pos]}INSERT INTO {table_ref}\n{s[pos:]}"


def _split_sql_batches(sql: str) -> list:
    """拆分批处理语句。优先按独立行 GO 拆分（支持 BEGIN/END）；否则按分号。"""
    text = sql.strip()
    if not text:
        return []
    if re.search(r'(?im)^\s*GO\s*$', text):
        parts = re.split(r'(?im)^\s*GO\s*$', text)
        return [p.strip() for p in parts if p.strip()]
    return [p.strip() for p in text.split(';') if p.strip()]


def _stmt_label(stmt: str) -> str:
    head = ' '.join(stmt.strip().split())[:80]
    return head


def _execute_script(db, sql: str, params: tuple = None, *, debug: bool = False) -> int:
    """同一连接顺序执行多条语句（保证 #临时表 可见）。"""
    batches = _split_sql_batches(sql)
    if not batches:
        return 0
    rowcount = 0
    total = len(batches)
    with db.get_connection() as conn:
        cursor = db.adapter.get_cursor(conn)
        for i, stmt in enumerate(batches):
            label = _stmt_label(stmt)
            if debug or label.upper().startswith(('SELECT', 'INSERT', 'CREATE', 'DELETE', 'TRUNCATE')):
                logger.info('BI SQL [%s/%s] %s', i + 1, total, label)
            if params is not None and i == 0 and '?' in stmt:
                cursor.execute(stmt, params)
            else:
                cursor.execute(stmt)
            if cursor.rowcount is not None and cursor.rowcount > 0:
                rowcount = cursor.rowcount
        # INSERT 在 SET NOCOUNT / 部分驱动下 rowcount 可能为 -1，用 @@ROWCOUNT 兜底
        if rowcount <= 0:
            try:
                cursor.execute('SELECT @@ROWCOUNT AS n')
                row = cursor.fetchone()
                if row is not None:
                    rowcount = int(row[0] if not isinstance(row, dict) else list(row.values())[0])
            except Exception:
                pass
        db.adapter.commit(conn)
    return max(rowcount, 0)


def run_bi_task(
    task_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    *,
    past_value=None,
    past_unit: Optional[str] = None,
    past_days: Optional[int] = None,
    mode: str = 'auto',
    debug: bool = False,
) -> int:
    """
    执行 BI 计算任务。

    mode:
        auto   - 目标表无数据时全量写入区间；否则仅重算日期窗口（delete + insert）
        full   - 清空目标表后写入区间
        window - 仅重算 [start_date, end_date] 窗口（delete + insert）
    """
    _ensure_console_log()
    task = get_task(task_name)
    if not task:
        from .registry import list_tasks
        names = [t.name for t in list_tasks()]
        raise ValueError(f'未知 BI 任务: {task_name}，可选: {names}')

    if not task.build_batch_sql and not task.build_select_sql:
        raise ValueError(f'任务 {task_name} 需定义 build_batch_sql 或 build_select_sql')

    db = get_db_manager()
    if db.db_config.type.lower() != 'sqlserver':
        raise RuntimeError('BI 计算任务当前仅支持 SQL Server')

    start_date, end_date = resolve_bi_date_range(
        start_date, end_date, past_value, past_unit, past_days,
    )
    if start_date > end_date:
        raise ValueError(f'开始日期不能晚于结束日期: {start_date} ~ {end_date}')

    mode = (mode or 'auto').strip().lower()
    if mode not in ('auto', 'full', 'window'):
        raise ValueError(f'未知 mode: {mode}，可选: auto/full/window')

    _ensure_table(db, task)
    has_rows = _target_has_rows(db, task)

    if mode == 'auto':
        effective_mode = 'full' if not has_rows else 'window'
    else:
        effective_mode = mode

    date_col = task.date_column
    table_ref = _target_table_ref(task)

    logger.info(
        'BI 任务 %s (%s): %s ~ %s, mode=%s (effective=%s), 目标表=%s (has_rows=%s)',
        task.name, task.label, start_date, end_date, mode, effective_mode, table_ref, has_rows,
    )

    if task.build_batch_sql:
        if effective_mode == 'full':
            prep = f'TRUNCATE TABLE {table_ref}'
            params = None
        else:
            prep = f'DELETE FROM {table_ref} WHERE [{date_col}] >= ? AND [{date_col}] <= ?'
            params = (start_date, end_date)
        batch = task.batch_sql(start_date, end_date, table_ref).strip()
        sql = prep + '\nGO\n' + batch
        if debug:
            logger.info('BI batch SQL:\n%s', sql)
        n = _execute_script(db, sql, params, debug=debug)
        logger.info('BI 任务 %s %s完成，写入 %s 行', task.name, '全量' if effective_mode == 'full' else '窗口增量', n)
        return n

    select_sql = task.select_sql(start_date, end_date).strip()

    if effective_mode == 'full':
        delete_sql = f'TRUNCATE TABLE {table_ref};'
        insert_sql = _build_insert_sql(table_ref, select_sql) + ';'
        sql = delete_sql + insert_sql
        if debug:
            logger.info('BI SQL:\n%s', sql.strip())
        n = db.execute(sql.strip())
        logger.info('BI 任务 %s 全量完成，写入 %s 行', task.name, n)
        return n

    delete_sql = f"""
DELETE FROM {table_ref}
WHERE [{date_col}] >= ? AND [{date_col}] <= ?;
"""
    insert_sql = _build_insert_sql(table_ref, select_sql) + ';'
    if debug:
        logger.info('BI delete SQL:\n%s\nparams: (%s, %s)', delete_sql.strip(), start_date, end_date)
        logger.info('BI insert SQL:\n%s', insert_sql.strip())

    deleted = db.execute(delete_sql.strip(), (start_date, end_date))
    inserted = db.execute(insert_sql.strip())
    logger.info(
        'BI 任务 %s 窗口增量完成，删除 %s 行，写入 %s 行',
        task.name, deleted, inserted,
    )
    return inserted
