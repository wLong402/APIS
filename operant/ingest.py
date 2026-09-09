# -*- coding: utf-8 -*-
"""把 OperantID 下载的文件解析成行并写入数据库。"""

import csv
import hashlib
import json
import os
import re
from typing import Dict, List

from common.base_repository import BaseRepository

_TABLE_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
_FILE_EXTS = ('.csv', '.tsv', '.json', '.xlsx', '.xls')


def sanitize_table_name(name: str) -> str:
    raw = (name or '').strip()
    if raw.startswith('operant_'):
        raw = raw[len('operant_'):]
    if not raw or not _TABLE_RE.match(raw):
        raise ValueError(f'非法目标表名: {name}（仅允许字母数字下划线，将写入 operant_<name>）')
    return raw


class OperantDownloadRepository(BaseRepository):
    SYSTEM_PREFIX = 'operant'

    def __init__(self, table_name: str, unique_key: str = 'rowKey'):
        self.TABLE_NAME = sanitize_table_name(table_name)
        self.UNIQUE_KEY = unique_key or 'rowKey'
        super().__init__()


def _row_key(item: Dict) -> str:
    raw = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def attach_row_keys(rows: List[Dict], unique_key: str) -> List[Dict]:
    out = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        if unique_key and unique_key != 'rowKey' and row.get(unique_key) not in (None, ''):
            out.append(row)
            continue
        if not row.get('rowKey'):
            row['rowKey'] = _row_key(row)
        out.append(row)
    return out


def parse_file(path: str) -> List[Dict]:
    ext = os.path.splitext(path)[1].lower()
    if ext == '.json':
        with open(path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            for key in ('data', 'items', 'rows', 'records'):
                val = data.get(key)
                if isinstance(val, list):
                    return [x for x in val if isinstance(x, dict)]
            return [data]
        return []
    if ext in ('.xlsx', '.xls'):
        try:
            import pandas as pd
        except ImportError as e:
            raise RuntimeError('读取 Excel 需要 pandas') from e
        df = pd.read_excel(path)
        return df.where(df.notna(), None).to_dict(orient='records')
    delimiter = '\t' if ext == '.tsv' else ','
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return [{k: (v if v != '' else None) for k, v in row.items()} for row in reader]


def parse_result_message(message) -> List[Dict]:
    if not message:
        return []
    text = message if isinstance(message, str) else json.dumps(message, ensure_ascii=False)
    text = text.strip()
    try:
        data = json.loads(text)
    except Exception:
        start = text.find('[')
        end = text.rfind(']')
        if start < 0 or end <= start:
            return []
        try:
            data = json.loads(text[start:end + 1])
        except Exception:
            return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ('data', 'items', 'rows', 'records'):
            val = data.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
    return []


def list_data_files(directory: str) -> List[str]:
    if not directory or not os.path.isdir(directory):
        return []
    files = []
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        if os.path.isfile(path) and name.lower().endswith(_FILE_EXTS):
            files.append(path)
    files.sort(key=lambda p: os.path.getmtime(p))
    return files


def ingest_files(
    paths: List[str],
    table_name: str,
    unique_key: str = 'rowKey',
    debug: bool = False,
) -> int:
    rows: List[Dict] = []
    for path in paths:
        parsed = parse_file(path)
        print(f'    [INGEST] {os.path.basename(path)} -> {len(parsed)} 行', flush=True)
        rows.extend(parsed)
    if not rows:
        return 0
    rows = attach_row_keys(rows, unique_key)
    uk = unique_key if unique_key and any(r.get(unique_key) not in (None, '') for r in rows) else 'rowKey'
    repo = OperantDownloadRepository(table_name, unique_key=uk)
    return repo.save_batch(rows, debug=debug, progress_label=f'operant.{repo.full_table_name}')
