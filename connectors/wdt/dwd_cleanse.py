# -*- coding: utf-8 -*-

import logging
from typing import Any, Dict, List, Optional, Set

from connectors.wechat_store.services.author_talent_mapping import (
    enrich_profits_live_order_talent_id,
    enrich_profits_live_refund_talent_id,
)
from core.database import get_db_manager
from core.logger import DATE_FORMAT, LOG_FORMAT, get_logger

logger = get_logger('wdt.dwd')

DWD_PULL_SERVICE: Dict[str, str] = {
    'aftersales_refund': 'aftersales_refund',
    'profits_live_order': 'profits_live_order',
    'profits_live_refund': 'profits_live_refund',
}

DWD_TASK_LABEL: Dict[str, str] = {
    'aftersales_refund': '售后退款 → DWD',
    'profits_live_order': '利润表明细(订单) → DWD',
    'profits_live_refund': '利润表明细(退款) → DWD',
}

# DWD 后写入字段：ODS 无对应列，MERGE/INSERT 不能从 ODS 选取
DWD_ENRICHMENT_COLUMNS = frozenset({'talent_id'})


def pull_service_to_dwd_task(service: str) -> Optional[str]:
    if not service:
        return None
    for task, svc in DWD_PULL_SERVICE.items():
        if svc == service:
            return task
    return None

TRUNC_AFTERSALES_REFUND = r"""
TRUNCATE TABLE dbo.dwd_wdt_aftersales_refund;
"""

INSERT_AFTERSALES_REFUND = r"""
WITH CTE_Header AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY refund_id ORDER BY modified DESC) AS rn
    FROM dbo.wdt_aftersales_refund
)
INSERT INTO dbo.dwd_wdt_aftersales_refund (
    refund_id, fenxiao_nick, warehouse_type, provider_refund_no, refund_no,
    bad_reason, return_telno, type_, trade_id, current_phase_timeout, fenxiao_nick_name,
    wms_owner_no, modified_time, order_type, shop_no, created_time, return_logistics_no,
    trade_no_list, return_goods_amount, rr_status, modified_date, shop_platform_id,
    shop_id, src_tids, actual_refund_amount, refund_time, process_status,
    fenxiao_distributor_name, receive_amount, pay_id, check_time, status_,
    return_mask_info, tmp_data, tid_list, fenxiao_distributor_id, remark,
    sub_platform_id, stockin_status, flag_name, return_goods_count, receiver_telno,
    wms_code, receiver_name, refund_reason, return_warehouse_id, note_count, from_type,
    raw_refund_nos, fenxiao_alias,
    consign_mode,
    guarantee_refund_amount, return_logistics_name,
    settle_time, reason_id, buyer_nick,
    operator_name, revert_reason, return_warehouse_no, direct_refund_amount,
    platform_id, sync_return, customer_name, reason_name, customer_id, return_mask,
    revert_reason_name
)
SELECT
    refund_id, fenxiao_nick, warehouse_type, provider_refund_no, refund_no,
    bad_reason, return_telno, type_, trade_id, current_phase_timeout, fenxiao_nick_name,
    wms_owner_no, DATEADD(SECOND, modified / 1000, '1970-01-01'), order_type, shop_no,
    DATEADD(SECOND, created / 1000, '1970-01-01'), return_logistics_no,
    trade_no_list, TRY_CAST(return_goods_amount AS DECIMAL(19,4)), rr_status, modified_date, shop_platform_id,
    shop_id, src_tids, TRY_CAST(actual_refund_amount AS DECIMAL(19,4)), TRY_CAST(refund_time AS DATETIME), process_status,
    fenxiao_distributor_name, TRY_CAST(receive_amount AS DECIMAL(19,4)), pay_id, TRY_CAST(check_time AS DATETIME), status_,
    return_mask_info, tmp_data, tid_list, fenxiao_distributor_id, remark,
    sub_platform_id, stockin_status, flag_name, TRY_CAST(return_goods_count AS DECIMAL(19,4)), receiver_telno,
    wms_code, receiver_name, refund_reason, return_warehouse_id, note_count, from_type,
    raw_refund_nos, fenxiao_alias,
    consign_mode,
    TRY_CAST(guarantee_refund_amount AS DECIMAL(19,4)), return_logistics_name,
    settle_time, reason_id, buyer_nick,
    operator_name, revert_reason, return_warehouse_no, TRY_CAST(direct_refund_amount AS DECIMAL(19,4)),
    platform_id, sync_return, customer_name, reason_name, customer_id, return_mask,
    revert_reason_name
FROM CTE_Header
WHERE rn = 1;
"""

SQL_DWD_TASKS = {
    'aftersales_refund': (TRUNC_AFTERSALES_REFUND, INSERT_AFTERSALES_REFUND),
}

ALL_DWD_TASK_NAMES: tuple = tuple(sorted(set(SQL_DWD_TASKS.keys()) | {'profits_live_order', 'profits_live_refund'}))


def _job_is_wdt_success_pull(j: Dict[str, Any]) -> bool:
    if j.get('connector') != 'wdt':
        return False
    if j.get('status') != 'success' or j.get('exit_code') != 0:
        return False
    if j.get('run_mode') == 'dwd':
        return False
    if j.get('run_mode') == 'pull':
        return True
    cmd = (j.get('cmd') or '') + ' '
    if ' dwd ' in cmd or ' dwd\n' in j.get('cmd') or (j.get('cmd') or '').strip().endswith(' dwd'):
        return False
    return 'pull' in cmd


def dwd_tasks_unlocked_by_jobs(jobs: List[Dict[str, Any]]) -> List[str]:
    unlocked: Set[str] = set()
    for j in jobs:
        if not _job_is_wdt_success_pull(j):
            continue
        svc = j.get('service')
        if not svc:
            continue
        for task, pull_svc in DWD_PULL_SERVICE.items():
            if pull_svc == svc:
                unlocked.add(task)
    return sorted(unlocked)


def available_dwd_task_options(jobs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [
        {'id': t, 'label': DWD_TASK_LABEL.get(t, t)}
        for t in dwd_tasks_unlocked_by_jobs(jobs)
    ]


# profits_live_order：dbo.wdt_profits_live_order → dbo.dwd_wdt_profits_live_order（与 wdt_aftersales_refund 无关）


PROFITS_LIVE_ORDER_DWD_SQL_TYPES: Dict[str, str] = {
    'commissionrate': 'DECIMAL(10,4)',
    'costamount': 'DECIMAL(19,4)',
    'receivableamount': 'DECIMAL(19,4)',
    'postfee': 'DECIMAL(19,4)',
    'giftfee': 'DECIMAL(19,4)',
    'packingfee': 'DECIMAL(19,4)',
    'postamount': 'DECIMAL(19,4)',
    'investmentpromotionamount': 'DECIMAL(19,4)',
    'investmentpromotionrate': 'DECIMAL(10,4)',
    'realcommission': 'DECIMAL(19,4)',
    'residueamount': 'DECIMAL(19,4)',
    'payqty': 'INT',
    'deliverytime': 'DATETIME',
    'ordertime': 'DATETIME',
    'paytime': 'DATETIME',
    'finishtime': 'DATETIME',
    'created_at': 'DATETIME',
    'updated_at': 'DATETIME',
}

# ODS 实测最大字符长度 → DWD 列宽 = max(ods_max * 3, 30)
PROFITS_LIVE_ORDER_ODS_MAX_LEN: Dict[str, int] = {
    'activityuserid': 19,
    'activityusername': 6,
    'authorid': 24,
    'authorname': 20,
    'datano': 32,
    'flowtypename': 7,
    'isspecordername': 3,
    'livesessionid': 19,
    'omsgoodsname': 33,
    'omsgoodsno': 13,
    'omsorderno': 22,
    'omsspecname': 17,
    'omsspecno': 13,
    'ordersourcename': 7,
    'platgoodsid': 24,
    'platgoodsname': 73,
    'platorderno': 19,
    'platspecid': 24,
    'platspecname': 81,
    'platsubno': 40,
    'prop1': 0,
    'prop2': 0,
    'prop3': 0,
    'prop4': 0,
    'prop5': 0,
    'prop6': 0,
    'roomid': 103,
    'salespersonname': 3,
    'sessionno': 11,
    'shopname': 29,
    'teamname': 8,
    'toolsdesc': 3,
    'rowkey': 32,
    'suiteno': 15,
}


def _dwd_varchar_width(ods_max_len: int) -> int:
    if ods_max_len <= 0:
        return 30
    return min(ods_max_len * 3, 4000)


PROFITS_LIVE_ORDER_DWD_VARCHAR_WIDTHS: Dict[str, int] = {
    k: _dwd_varchar_width(v) for k, v in PROFITS_LIVE_ORDER_ODS_MAX_LEN.items()
}


PROFITS_LIVE_REFUND_DWD_SQL_TYPES: Dict[str, str] = {
    'commissionrate': 'DECIMAL(10,4)',
    'investmentpromotionamount': 'DECIMAL(19,4)',
    'investmentpromotionrate': 'DECIMAL(10,4)',
    'realcommission': 'DECIMAL(19,4)',
    'refundamount': 'DECIMAL(19,4)',
    'refundcost': 'DECIMAL(19,4)',
    'refundgiftfee': 'DECIMAL(19,4)',
    'shareplatdiscountamount': 'DECIMAL(19,4)',
    'refundqty': 'INT',
    'deliverytime': 'DATETIME',
    'paytime': 'DATETIME',
    'refunddate': 'DATETIME',
    'finishtime': 'DATETIME',
    'created_at': 'DATETIME',
    'updated_at': 'DATETIME',
}

PROFITS_LIVE_REFUND_ODS_MAX_LEN: Dict[str, int] = {
    'activityuserid': 15,
    'activityusername': 4,
    'authorid': 24,
    'authorname': 20,
    'datano': 32,
    'flowtypename': 7,
    'livesessionid': 19,
    'omsgoodsname': 33,
    'omsgoodsno': 13,
    'omsspecname': 17,
    'omsspecno': 13,
    'ordersourcename': 7,
    'platgoodsid': 24,
    'platgoodsname': 69,
    'platorderno': 19,
    'platrefundno': 18,
    'platspecid': 24,
    'platspecname': 70,
    'platsubno': 40,
    'prop1': 0,
    'prop2': 0,
    'prop3': 0,
    'prop4': 0,
    'prop5': 0,
    'prop6': 0,
    'refundstatusname': 4,
    'refundtypename': 9,
    'roomid': 57,
    'salespersonname': 3,
    'sessionno': 11,
    'shopname': 21,
    'teamname': 8,
    'toolsdesc': 3,
    'rowkey': 32,
    'omsrefundno': 22,
    'suiteno': 15,
}

PROFITS_LIVE_REFUND_DWD_VARCHAR_WIDTHS: Dict[str, int] = {
    k: _dwd_varchar_width(v) for k, v in PROFITS_LIVE_REFUND_ODS_MAX_LEN.items()
}


def _dwd_physical_col_name(db, table_name: str, col_lower: str) -> Optional[str]:
    r = db.fetch_one(
        """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = N'dbo' AND TABLE_NAME = ? AND LOWER(COLUMN_NAME) = LOWER(?)
        """,
        (table_name, col_lower),
    )
    if not r:
        return None
    return list(r.values())[0]


_profits_live_order_physical_col_name = _dwd_physical_col_name


def _ensure_profits_live_order_dwd_types(db, dwd: str) -> None:
    for col_lower, sql_type in PROFITS_LIVE_ORDER_DWD_SQL_TYPES.items():
        phys = _profits_live_order_physical_col_name(db, dwd, col_lower)
        if not phys:
            continue
        dt = db.fetch_one(
            """
            SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = N'dbo' AND TABLE_NAME = ? AND COLUMN_NAME = ?
            """,
            (dwd, phys),
        )
        cur = (list(dt.values())[0] if dt else '').lower()
        if cur not in ('varchar', 'nvarchar', 'char', 'nchar'):
            continue
        db.execute(f'ALTER TABLE dbo.[{dwd}] ALTER COLUMN [{phys}] {sql_type} NULL')
        logger.info('dwd %s: ALTER [%s] -> %s', dwd, phys, sql_type)


def _ensure_profits_live_order_dwd_varchar_widths(db, dwd: str) -> None:
    for col_lower, w in PROFITS_LIVE_ORDER_DWD_VARCHAR_WIDTHS.items():
        if col_lower == 'datano':
            continue
        phys = _profits_live_order_physical_col_name(db, dwd, col_lower)
        if not phys:
            continue
        dt_row = db.fetch_one(
            """
            SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = N'dbo' AND TABLE_NAME = ? AND COLUMN_NAME = ?
            """,
            (dwd, phys),
        )
        cur = (list(dt_row.values())[0] if dt_row else '').lower()
        if cur not in ('varchar', 'nvarchar', 'char', 'nchar'):
            continue
        sql_type = f'NVARCHAR({w})'
        db.execute(f'ALTER TABLE dbo.[{dwd}] ALTER COLUMN [{phys}] {sql_type} NULL')
        logger.info('dwd %s: ALTER [%s] -> %s', dwd, phys, sql_type)


def _profits_live_order_src_expr(col: str) -> str:
    b = col.lower()
    q = f'[{col}]'
    if b == 'commissionrate':
        return f"TRY_CAST(REPLACE({q}, '%', '') AS DECIMAL(10,4)) / 100.0 AS {q}"
    if b in (
        'costamount',
        'receivableamount',
        'postfee',
        'giftfee',
        'packingfee',
        'postamount',
        'investmentpromotionamount',
        'realcommission',
        'residueamount',
    ):
        return f"TRY_CAST(REPLACE(REPLACE({q}, ',', ''), N'¥', '') AS DECIMAL(19,4)) AS {q}"
    if b == 'investmentpromotionrate':
        return f"TRY_CAST(REPLACE({q}, '%', '') AS DECIMAL(10,4)) / 100.0 AS {q}"
    if b == 'payqty':
        return f"TRY_CAST({q} AS INT) AS {q}"
    if b in ('deliverytime', 'ordertime', 'paytime', 'finishtime', 'created_at', 'updated_at'):
        return f"TRY_CAST({q} AS DATETIME) AS {q}"
    return q


def _profits_live_order_src_select_list(insert_cols: List[str]) -> str:
    return ', '.join(_profits_live_order_src_expr(c) for c in insert_cols)


def _ensure_profits_live_refund_dwd_types(db, dwd: str) -> None:
    for col_lower, sql_type in PROFITS_LIVE_REFUND_DWD_SQL_TYPES.items():
        phys = _dwd_physical_col_name(db, dwd, col_lower)
        if not phys:
            continue
        dt = db.fetch_one(
            """
            SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = N'dbo' AND TABLE_NAME = ? AND COLUMN_NAME = ?
            """,
            (dwd, phys),
        )
        cur = (list(dt.values())[0] if dt else '').lower()
        if cur not in ('varchar', 'nvarchar', 'char', 'nchar'):
            continue
        db.execute(f'ALTER TABLE dbo.[{dwd}] ALTER COLUMN [{phys}] {sql_type} NULL')
        logger.info('dwd %s: ALTER [%s] -> %s', dwd, phys, sql_type)


def _ensure_profits_live_refund_dwd_varchar_widths(db, dwd: str) -> None:
    for col_lower, w in PROFITS_LIVE_REFUND_DWD_VARCHAR_WIDTHS.items():
        if col_lower == 'datano':
            continue
        phys = _dwd_physical_col_name(db, dwd, col_lower)
        if not phys:
            continue
        dt_row = db.fetch_one(
            """
            SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = N'dbo' AND TABLE_NAME = ? AND COLUMN_NAME = ?
            """,
            (dwd, phys),
        )
        cur = (list(dt_row.values())[0] if dt_row else '').lower()
        if cur not in ('varchar', 'nvarchar', 'char', 'nchar'):
            continue
        sql_type = f'NVARCHAR({w})'
        db.execute(f'ALTER TABLE dbo.[{dwd}] ALTER COLUMN [{phys}] {sql_type} NULL')
        logger.info('dwd %s: ALTER [%s] -> %s', dwd, phys, sql_type)


def _profits_live_refund_src_expr(col: str) -> str:
    b = col.lower()
    q = f'[{col}]'
    if b in ('commissionrate', 'investmentpromotionrate'):
        return f"TRY_CAST(REPLACE({q}, '%', '') AS DECIMAL(10,4)) / 100.0 AS {q}"
    if b in (
        'investmentpromotionamount',
        'realcommission',
        'refundamount',
        'refundcost',
        'refundgiftfee',
        'shareplatdiscountamount',
    ):
        return f"TRY_CAST(REPLACE(REPLACE({q}, ',', ''), N'¥', '') AS DECIMAL(19,4)) AS {q}"
    if b == 'refundqty':
        return f"TRY_CAST({q} AS INT) AS {q}"
    if b in (
        'deliverytime',
        'paytime',
        'refunddate',
        'finishtime',
        'created_at',
        'updated_at',
        'createdat',
        'updatedat',
    ):
        return f"TRY_CAST({q} AS DATETIME) AS {q}"
    return q


def _profits_live_refund_src_select_list(insert_cols: List[str]) -> str:
    return ', '.join(_profits_live_refund_src_expr(c) for c in insert_cols)


def _ordered_ods_columns(db, table_name: str) -> List[str]:
    rows = db.fetch_all(
        """
        SELECT LOWER(COLUMN_NAME) AS col_name
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
        """,
        (table_name,),
    )
    return [r['col_name'] for r in rows]


def _dwd_merge_insert_cols(db, ods: str, dwd: str, id_cols: Set[str]) -> List[str]:
    """DWD 列序下，仅保留 ODS 也有的列（排除标识列与后写入 enrichment 列）。"""
    dwd_cols = _ordered_ods_columns(db, dwd)
    ods_cols = set(_ordered_ods_columns(db, ods))
    merge_cols = [
        c for c in dwd_cols
        if c not in id_cols
        and c in ods_cols
        and c not in DWD_ENRICHMENT_COLUMNS
    ]
    skipped = [c for c in dwd_cols if c in DWD_ENRICHMENT_COLUMNS and c not in id_cols]
    if skipped:
        logger.debug('dwd %s: MERGE 跳过 ODS 无来源列 %s', dwd, skipped)
    return merge_cols


def _identity_column_names_sqlserver(db, table_name: str) -> List[str]:
    rows = db.fetch_all(
        """
        SELECT LOWER(c.name) AS col_name
        FROM sys.columns c
        INNER JOIN sys.tables t ON c.object_id = t.object_id AND t.schema_id = SCHEMA_ID(N'dbo')
        WHERE t.name = ? AND c.is_identity = 1
        """,
        (table_name,),
    )
    return [r['col_name'] for r in rows]


def _dwd_profits_live_order_pk_name(db, dwd: str) -> Optional[str]:
    r = db.fetch_one(
        """
        SELECT k.name
        FROM sys.key_constraints k
        INNER JOIN sys.tables t ON k.parent_object_id = t.object_id AND t.schema_id = SCHEMA_ID(N'dbo')
        WHERE t.name = ? AND k.type = N'PK'
        """,
        (dwd,),
    )
    return list(r.values())[0] if r else None


def _dwd_profits_live_order_pk_columns_lower(db, dwd: str) -> List[str]:
    rows = db.fetch_all(
        """
        SELECT LOWER(c.name) AS col_name
        FROM sys.indexes i
        INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        INNER JOIN sys.tables t ON i.object_id = t.object_id AND t.schema_id = SCHEMA_ID(N'dbo')
        WHERE t.name = ? AND i.is_primary_key = 1
        ORDER BY ic.key_ordinal
        """,
        (dwd,),
    )
    return [r['col_name'] for r in rows]


def _ensure_dwd_datano_pk(db, dwd: str, datano_width: int) -> None:
    phys = _dwd_physical_col_name(db, dwd, 'datano')
    if not phys:
        raise RuntimeError('DWD 表缺少 dataNo 列')
    cur_pk_cols = _dwd_profits_live_order_pk_columns_lower(db, dwd)
    if cur_pk_cols == ['datano']:
        return
    pk_name = _dwd_profits_live_order_pk_name(db, dwd)
    if pk_name:
        db.execute(f'ALTER TABLE dbo.[{dwd}] DROP CONSTRAINT [{pk_name}]')
        logger.info('dwd %s: DROP PK [%s]', dwd, pk_name)
    w = int(datano_width)
    db.execute(f'ALTER TABLE dbo.[{dwd}] ALTER COLUMN [{phys}] NVARCHAR({w}) NOT NULL')
    cstr = f'PK_{dwd}'
    db.execute(f'ALTER TABLE dbo.[{dwd}] ADD CONSTRAINT [{cstr}] PRIMARY KEY ([{phys}])')
    logger.info('dwd %s: ADD PK [%s] ON [%s]', dwd, cstr, phys)


def _run_dwd_profits_live_refund(db, debug: bool = False) -> int:
    ods = 'wdt_profits_live_refund'
    dwd = 'dwd_wdt_profits_live_refund'
    if not db.table_exists(ods):
        raise RuntimeError(f'ODS 表 {ods} 不存在，请先拉取 profits_live_refund')
    db.execute(
        f"IF OBJECT_ID(N'dbo.{dwd}', N'U') IS NULL "
        f"SELECT TOP 0 * INTO dbo.{dwd} FROM dbo.{ods};"
    )
    _ensure_profits_live_refund_dwd_types(db, dwd)
    _ensure_profits_live_refund_dwd_varchar_widths(db, dwd)
    _ensure_dwd_datano_pk(db, dwd, PROFITS_LIVE_REFUND_DWD_VARCHAR_WIDTHS.get('datano', 96))
    cols = _ordered_ods_columns(db, dwd)
    if 'datano' not in cols:
        raise RuntimeError('ODS/DWD 缺少 dataNo 列，无法清洗')
    id_cols = set(_identity_column_names_sqlserver(db, dwd))
    insert_cols = _dwd_merge_insert_cols(db, ods, dwd, id_cols)
    if not insert_cols:
        raise RuntimeError('DWD 表无可插入列（可能全部为标识列）')
    qcols = ', '.join(f'[{c}]' for c in insert_cols)
    select_src = _profits_live_refund_src_select_list(insert_cols)
    if 'paytime' in cols:
        order_by = 'ORDER BY [paytime] DESC'
    elif 'refunddate' in cols:
        order_by = 'ORDER BY [refunddate] DESC'
    elif 'id' in cols:
        order_by = 'ORDER BY [id] DESC'
    else:
        order_by = 'ORDER BY (SELECT NULL)'

    row = db.fetch_one(f'SELECT COUNT_BIG(*) AS n FROM dbo.[{dwd}]')
    n_existing = int(list(row.values())[0]) if row else 0

    cte = f"""
;WITH _dwd_cte AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY [datano] {order_by}) AS _dwd_rn
    FROM dbo.[{ods}]
),
src AS (
    SELECT {select_src} FROM _dwd_cte WHERE _dwd_rn = 1
)"""

    if n_existing == 0:
        logger.info('dwd profits_live_refund: 全量（目标表无数据）')
        sql = f"""
{cte}
INSERT INTO dbo.[{dwd}] ({qcols})
SELECT {qcols} FROM src;
"""
        if debug:
            logger.info('dwd profits_live_refund SQL:\n%s', sql.strip())
        n = db.execute(sql.strip())
    else:
        upd_cols = [c for c in insert_cols if c != 'datano']
        update_set = ', '.join(f'tgt.[{c}] = src.[{c}]' for c in upd_cols)
        vals = ', '.join(f'src.[{c}]' for c in insert_cols)
        logger.info('dwd profits_live_refund: 增量 MERGE（目标表已有 %s 行）', n_existing)
        merge_sql = f"""
{cte}
MERGE dbo.[{dwd}] AS tgt
USING src ON tgt.[datano] = src.[datano]
WHEN MATCHED THEN UPDATE SET {update_set}
WHEN NOT MATCHED BY TARGET THEN INSERT ({qcols}) VALUES ({vals});
"""
        if debug:
            logger.info('dwd profits_live_refund SQL:\n%s', merge_sql.strip())
        n = db.execute(merge_sql.strip())

    try:
        n_talent = enrich_profits_live_refund_talent_id(db, ods_table=ods, dwd_table=dwd, debug=debug)
        logger.info('dwd profits_live_refund: talent_id 回填完成，更新 %s 行', n_talent)
    except Exception as exc:
        logger.exception('dwd profits_live_refund: talent_id 回填失败（不影响主清洗）: %s', exc)
    return n


def _run_dwd_profits_live_order(db, debug: bool = False) -> int:
    ods = 'wdt_profits_live_order'
    dwd = 'dwd_wdt_profits_live_order'
    if not db.table_exists(ods):
        raise RuntimeError(f'ODS 表 {ods} 不存在，请先拉取 profits_live_order')
    db.execute(
        f"IF OBJECT_ID(N'dbo.{dwd}', N'U') IS NULL "
        f"SELECT TOP 0 * INTO dbo.{dwd} FROM dbo.{ods};"
    )
    _ensure_profits_live_order_dwd_types(db, dwd)
    _ensure_profits_live_order_dwd_varchar_widths(db, dwd)
    _ensure_dwd_datano_pk(db, dwd, PROFITS_LIVE_ORDER_DWD_VARCHAR_WIDTHS.get('datano', 96))
    cols = _ordered_ods_columns(db, dwd)
    if 'datano' not in cols:
        raise RuntimeError('ODS/DWD 缺少 dataNo 列，无法清洗')
    id_cols = set(_identity_column_names_sqlserver(db, dwd))
    insert_cols = _dwd_merge_insert_cols(db, ods, dwd, id_cols)
    if not insert_cols:
        raise RuntimeError('DWD 表无可插入列（可能全部为标识列）')
    qcols = ', '.join(f'[{c}]' for c in insert_cols)
    select_src = _profits_live_order_src_select_list(insert_cols)
    if 'ordertime' in cols:
        order_by = 'ORDER BY [ordertime] DESC'
    elif 'id' in cols:
        order_by = 'ORDER BY [id] DESC'
    else:
        order_by = 'ORDER BY (SELECT NULL)'

    row = db.fetch_one(f'SELECT COUNT_BIG(*) AS n FROM dbo.[{dwd}]')
    n_existing = int(list(row.values())[0]) if row else 0

    cte = f"""
;WITH _dwd_cte AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY [datano] {order_by}) AS _dwd_rn
    FROM dbo.[{ods}]
),
src AS (
    SELECT {select_src} FROM _dwd_cte WHERE _dwd_rn = 1
)"""

    if n_existing == 0:
        logger.info('dwd profits_live_order: 全量（目标表无数据）')
        sql = f"""
{cte}
INSERT INTO dbo.[{dwd}] ({qcols})
SELECT {qcols} FROM src;
"""
        if debug:
            logger.info('dwd profits_live_order SQL:\n%s', sql.strip())
        n = db.execute(sql.strip())
    else:
        upd_cols = [c for c in insert_cols if c != 'datano']
        update_set = ', '.join(f'tgt.[{c}] = src.[{c}]' for c in upd_cols)
        vals = ', '.join(f'src.[{c}]' for c in insert_cols)
        logger.info('dwd profits_live_order: 增量 MERGE（目标表已有 %s 行）', n_existing)
        merge_sql = f"""
{cte}
MERGE dbo.[{dwd}] AS tgt
USING src ON tgt.[datano] = src.[datano]
WHEN MATCHED THEN UPDATE SET {update_set}
WHEN NOT MATCHED BY TARGET THEN INSERT ({qcols}) VALUES ({vals});
"""
        if debug:
            logger.info('dwd profits_live_order SQL:\n%s', merge_sql.strip())
        n = db.execute(merge_sql.strip())

    try:
        n_talent = enrich_profits_live_order_talent_id(db, ods_table=ods, dwd_table=dwd, debug=debug)
        logger.info('dwd profits_live_order: talent_id 回填完成，更新 %s 行', n_talent)
    except Exception as exc:
        logger.exception('dwd profits_live_order: talent_id 回填失败（不影响主清洗）: %s', exc)
    return n


def _ensure_dwd_console_log() -> None:
    for h in logger.handlers:
        if getattr(h, '_dwd_console', False):
            return
    sh = logging.StreamHandler()
    sh._dwd_console = True
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(sh)


def run_dwd_task(task: str, debug: bool = False) -> int:
    _ensure_dwd_console_log()
    db = get_db_manager()
    if db.db_config.type.lower() != 'sqlserver':
        raise RuntimeError('仅支持 SQL Server')

    if task == 'profits_live_refund':
        n = _run_dwd_profits_live_refund(db, debug=debug)
        logger.info(f'dwd task={task} 完成，插入行数: {n}')
        return n

    if task == 'profits_live_order':
        n = _run_dwd_profits_live_order(db, debug=debug)
        logger.info(f'dwd task={task} 完成，插入行数: {n}')
        return n

    steps = SQL_DWD_TASKS.get(task)
    if not steps:
        raise ValueError(f'未知任务: {task}，可选: {list(ALL_DWD_TASK_NAMES)}')

    last = 0
    for sql in steps:
        last = db.execute(sql.strip())
    logger.info(f'dwd task={task} 完成，插入行数: {last}')
    return last
