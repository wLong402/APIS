# -*- coding: utf-8 -*-
"""authorid → talent_id 映射：先查表，缺失则调微信订单接口解析并落库。"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.config import get_config
from core.database import get_db_manager
from core.logger import get_logger

from ..sdk import WechatStoreAPIClient, WechatStoreConfig

logger = get_logger('wechat_store.author_talent')

MAPPING_TABLE = 'dwd_authorid_talent_mapping'
DWD_TALENT_COLUMN = 'talent_id'


def _load_wechat_store_config() -> WechatStoreConfig:
    cfg = get_config()
    raw = cfg.connectors.get('wechat_store') or cfg._raw.get('wechat_store') or {}
    return WechatStoreConfig(
        appid=str(raw.get('appid') or ''),
        secret=str(raw.get('secret') or ''),
        timeout=int(raw.get('timeout') or 30),
        token_cache_path=str(raw.get('token_cache_path') or './wechat_store_token.conf'),
    )


def get_wechat_store_client() -> WechatStoreAPIClient:
    return WechatStoreAPIClient(_load_wechat_store_config())


def ensure_mapping_table(db) -> None:
    if db.table_exists(MAPPING_TABLE):
        return
    db.execute(
        f"""
        CREATE TABLE dbo.[{MAPPING_TABLE}] (
            [authorid] NVARCHAR(64) NOT NULL,
            [talent_id] NVARCHAR(64) NULL,
            [sample_platorderno] NVARCHAR(64) NULL,
            [authorname] NVARCHAR(128) NULL,
            [created_at] DATETIME NOT NULL DEFAULT GETDATE(),
            [updated_at] DATETIME NOT NULL DEFAULT GETDATE(),
            CONSTRAINT [PK_{MAPPING_TABLE}] PRIMARY KEY ([authorid])
        );
        """
    )
    logger.info('wechat_store mapping: 已创建表 dbo.%s', MAPPING_TABLE)


def ensure_dwd_talent_id_column(db, dwd_table: str) -> None:
    cols = {c.lower() for c in db.get_table_columns(dwd_table)}
    if DWD_TALENT_COLUMN in cols:
        return
    db.execute(f'ALTER TABLE dbo.[{dwd_table}] ADD [{DWD_TALENT_COLUMN}] NVARCHAR(64) NULL;')
    logger.info('dwd %s: 已新增列 [%s]', dwd_table, DWD_TALENT_COLUMN)


def extract_talent_id_from_order(order_resp: Dict[str, Any], author_id: str) -> Optional[str]:
    """从微信订单详情中，按 authorid（finder_id）匹配 talent_id。"""
    author_id = str(author_id or '').strip()
    if not author_id:
        return None

    order = order_resp.get('order') if isinstance(order_resp, dict) else None
    if not isinstance(order, dict):
        logger.debug('wechat_store mapping: 订单响应无 order 节点 authorid=%s', author_id)
        return None

    detail = order.get('order_detail') or {}
    commission_infos = detail.get('commission_infos') or []
    if isinstance(commission_infos, list):
        for info in commission_infos:
            if not isinstance(info, dict):
                continue
            finder_id = str(info.get('finder_id') or '').strip()
            openfinderid = str(info.get('openfinderid') or '').strip()
            if author_id in (finder_id, openfinderid):
                talent_id = str(info.get('talent_id') or '').strip()
                if talent_id:
                    logger.info(
                        'wechat_store mapping: 命中 commission_infos authorid=%s talent_id=%s finder_id=%s',
                        author_id,
                        talent_id,
                        finder_id,
                    )
                    return talent_id

    ext_info = detail.get('ext_info') or {}
    if isinstance(ext_info, dict):
        ext_finder = str(ext_info.get('finder_id') or '').strip()
        if ext_finder == author_id:
            logger.debug(
                'wechat_store mapping: ext_info.finder_id 匹配但无 talent_id authorid=%s',
                author_id,
            )

    logger.warning(
        'wechat_store mapping: 订单中未找到 talent_id authorid=%s order_id=%s',
        author_id,
        order.get('order_id'),
    )
    return None


def get_talent_id_from_mapping(db, author_id: str) -> Optional[str]:
    author_id = str(author_id or '').strip()
    if not author_id:
        return None
    row = db.fetch_one(
        f'SELECT [talent_id] FROM dbo.[{MAPPING_TABLE}] WHERE [authorid] = ?',
        (author_id,),
    )
    if not row:
        return None
    talent_id = str(list(row.values())[0] or '').strip()
    return talent_id or None


def upsert_mapping(
    db,
    author_id: str,
    talent_id: Optional[str],
    sample_platorderno: Optional[str] = None,
    authorname: Optional[str] = None,
) -> None:
    author_id = str(author_id or '').strip()
    if not author_id:
        return
    talent_id = str(talent_id or '').strip() or None
    sample_platorderno = str(sample_platorderno or '').strip() or None
    authorname = str(authorname or '').strip() or None
    now = datetime.now()

    existing = db.fetch_one(
        f'SELECT [authorid], [talent_id] FROM dbo.[{MAPPING_TABLE}] WHERE [authorid] = ?',
        (author_id,),
    )
    if existing:
        old_talent = str(existing.get('talent_id') or existing.get('TALENT_ID') or '').strip()
        if talent_id and talent_id != old_talent:
            db.execute(
                f"""
                UPDATE dbo.[{MAPPING_TABLE}]
                SET [talent_id] = ?, [sample_platorderno] = COALESCE(?, [sample_platorderno]),
                    [authorname] = COALESCE(?, [authorname]), [updated_at] = ?
                WHERE [authorid] = ?
                """,
                (talent_id, sample_platorderno, authorname, now, author_id),
            )
            logger.info(
                'wechat_store mapping: 更新 authorid=%s talent_id %s -> %s platorderno=%s',
                author_id,
                old_talent or '(空)',
                talent_id,
                sample_platorderno,
            )
        return

    db.execute(
        f"""
        INSERT INTO dbo.[{MAPPING_TABLE}]
            ([authorid], [talent_id], [sample_platorderno], [authorname], [created_at], [updated_at])
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (author_id, talent_id, sample_platorderno, authorname, now, now),
    )
    logger.info(
        'wechat_store mapping: 新增 authorid=%s talent_id=%s platorderno=%s',
        author_id,
        talent_id or '(空)',
        sample_platorderno,
    )


def resolve_talent_id_via_api(
    client: WechatStoreAPIClient,
    author_id: str,
    platorderno: str,
    debug: bool = False,
) -> Optional[str]:
    author_id = str(author_id or '').strip()
    platorderno = str(platorderno or '').strip()
    if not author_id or not platorderno:
        logger.warning(
            'wechat_store mapping: 跳过 API 解析，缺少 authorid 或 platorderno authorid=%s platorderno=%s',
            author_id,
            platorderno,
        )
        return None

    logger.info(
        'wechat_store mapping: 调用微信订单接口 authorid=%s platorderno=%s',
        author_id,
        platorderno,
    )
    order_resp = client.get_order(platorderno, debug=debug)
    return extract_talent_id_from_order(order_resp, author_id)


def _collect_pending_author_samples(db, ods_table: str, dwd_table: str) -> List[Dict[str, str]]:
    """收集 mapping 中缺失的 authorid，并各取一条 platorderno 样本。"""
    rows = db.fetch_all(
        f"""
        SELECT DISTINCT
            LTRIM(RTRIM(CAST(o.[authorid] AS NVARCHAR(64)))) AS authorid,
            LTRIM(RTRIM(CAST(o.[platorderno] AS NVARCHAR(64)))) AS platorderno,
            LTRIM(RTRIM(CAST(o.[authorname] AS NVARCHAR(128)))) AS authorname
        FROM dbo.[{ods_table}] o
        WHERE o.[authorid] IS NOT NULL
          AND LTRIM(RTRIM(CAST(o.[authorid] AS NVARCHAR(64)))) <> N''
          AND o.[platorderno] IS NOT NULL
          AND LTRIM(RTRIM(CAST(o.[platorderno] AS NVARCHAR(64)))) <> N''
          AND NOT EXISTS (
              SELECT 1 FROM dbo.[{MAPPING_TABLE}] m
              WHERE m.[authorid] = LTRIM(RTRIM(CAST(o.[authorid] AS NVARCHAR(64))))
                AND m.[talent_id] IS NOT NULL
                AND LTRIM(RTRIM(m.[talent_id])) <> N''
          )
        """
    )
    seen = set()
    samples: List[Dict[str, str]] = []
    for row in rows or []:
        authorid = str(row.get('authorid') or '').strip()
        platorderno = str(row.get('platorderno') or '').strip()
        if not authorid or not platorderno:
            continue
        key = authorid
        if key in seen:
            continue
        seen.add(key)
        samples.append({
            'authorid': authorid,
            'platorderno': platorderno,
            'authorname': str(row.get('authorname') or '').strip(),
        })
    return samples


def apply_mapping_to_dwd(db, dwd_table: str) -> int:
    """用 mapping 表回填 DWD.talent_id。"""
    n = db.execute(
        f"""
        UPDATE d
        SET d.[{DWD_TALENT_COLUMN}] = m.[talent_id]
        FROM dbo.[{dwd_table}] d
        INNER JOIN dbo.[{MAPPING_TABLE}] m
            ON LTRIM(RTRIM(CAST(d.[authorid] AS NVARCHAR(64)))) = m.[authorid]
        WHERE m.[talent_id] IS NOT NULL
          AND LTRIM(RTRIM(m.[talent_id])) <> N''
          AND (
              d.[{DWD_TALENT_COLUMN}] IS NULL
              OR LTRIM(RTRIM(d.[{DWD_TALENT_COLUMN}])) = N''
              OR LTRIM(RTRIM(d.[{DWD_TALENT_COLUMN}])) <> LTRIM(RTRIM(m.[talent_id]))
          )
        """
    )
    if n:
        logger.info('dwd %s: 从 mapping 回填 talent_id %s 行', dwd_table, n)
    return n


def enrich_live_dwd_talent_id(
    db=None,
    ods_table: str = 'wdt_profits_live_order',
    dwd_table: str = 'dwd_wdt_profits_live_order',
    task_label: str = 'profits_live_order',
    debug: bool = False,
    api_sleep_seconds: float = 0.15,
) -> int:
    """
    直播 DWD 写入后：确保 talent_id 列与 mapping 表，缺失 mapping 则调微信接口解析。
    返回 DWD 表 talent_id 被更新的总行数。
    """
    db = db or get_db_manager()
    ensure_mapping_table(db)
    ensure_dwd_talent_id_column(db, dwd_table)

    updated = apply_mapping_to_dwd(db, dwd_table)

    cfg = _load_wechat_store_config()
    if not cfg.appid or not cfg.secret:
        logger.warning(
            'wechat_store [%s]: 未配置 appid/secret，跳过 API 解析；请在 config.yaml 配置 wechat_store',
            task_label,
        )
        return updated

    pending = _collect_pending_author_samples(db, ods_table, dwd_table)
    if not pending:
        logger.info('wechat_store [%s] mapping: 无待解析 authorid，跳过 API', task_label)
        return updated

    logger.info('wechat_store [%s] mapping: 待 API 解析 authorid 数量=%s', task_label, len(pending))
    client = get_wechat_store_client()

    resolved = 0
    failed = 0
    for item in pending:
        authorid = item['authorid']
        cached = get_talent_id_from_mapping(db, authorid)
        if cached:
            logger.debug(
                'wechat_store [%s] mapping: 命中缓存 authorid=%s talent_id=%s',
                task_label,
                authorid,
                cached,
            )
            continue

        try:
            talent_id = resolve_talent_id_via_api(
                client,
                authorid,
                item['platorderno'],
                debug=debug,
            )
        except Exception as exc:
            failed += 1
            logger.error(
                'wechat_store [%s] mapping: API 解析失败 authorid=%s platorderno=%s err=%s',
                task_label,
                authorid,
                item['platorderno'],
                exc,
            )
            upsert_mapping(
                db,
                authorid,
                None,
                sample_platorderno=item['platorderno'],
                authorname=item.get('authorname'),
            )
            if api_sleep_seconds > 0:
                time.sleep(api_sleep_seconds)
            continue

        upsert_mapping(
            db,
            authorid,
            talent_id,
            sample_platorderno=item['platorderno'],
            authorname=item.get('authorname'),
        )
        if talent_id:
            resolved += 1
        else:
            failed += 1

        if api_sleep_seconds > 0:
            time.sleep(api_sleep_seconds)

    logger.info(
        'wechat_store [%s] mapping: API 解析完成 resolved=%s failed_or_empty=%s total=%s',
        task_label,
        resolved,
        failed,
        len(pending),
    )
    updated += apply_mapping_to_dwd(db, dwd_table)
    return updated


def enrich_profits_live_order_talent_id(
    db=None,
    ods_table: str = 'wdt_profits_live_order',
    dwd_table: str = 'dwd_wdt_profits_live_order',
    debug: bool = False,
    api_sleep_seconds: float = 0.15,
) -> int:
    return enrich_live_dwd_talent_id(
        db=db,
        ods_table=ods_table,
        dwd_table=dwd_table,
        task_label='profits_live_order',
        debug=debug,
        api_sleep_seconds=api_sleep_seconds,
    )


def enrich_profits_live_refund_talent_id(
    db=None,
    ods_table: str = 'wdt_profits_live_refund',
    dwd_table: str = 'dwd_wdt_profits_live_refund',
    debug: bool = False,
    api_sleep_seconds: float = 0.15,
) -> int:
    return enrich_live_dwd_talent_id(
        db=db,
        ods_table=ods_table,
        dwd_table=dwd_table,
        task_label='profits_live_refund',
        debug=debug,
        api_sleep_seconds=api_sleep_seconds,
    )
