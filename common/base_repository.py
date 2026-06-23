# -*- coding: utf-8 -*-
"""
数据仓库基类

提供数据存储的通用能力
"""

import json
from abc import ABC
from typing import Dict, List, Any, Optional, Set

from core.database import (
    DatabaseManager, get_db_manager, 
    sanitize_column_name, infer_column_type
)
from core.logger import get_logger, debug_print


class BaseRepository(ABC):
    """
    数据仓库基类
    
    子类必须定义:
        - TABLE_NAME: 表名（不含前缀）
        - UNIQUE_KEY: 唯一键字段名
        
    可选定义:
        - SYSTEM_PREFIX: 表名前缀（如 'wdt'）
    """
    
    # 表配置（子类必须定义）
    TABLE_NAME: str = None
    UNIQUE_KEY: str = None
    
    # 系统前缀（可选）
    SYSTEM_PREFIX: str = None

    # 预留列：接口偶发返回的稀疏字段，建表/补列时保证存在（子类可覆盖）
    # 例: {'roomId': 'NVARCHAR(64)', 'authorId': 'NVARCHAR(64)'}
    RESERVED_COLUMNS: Dict[str, str] = {}
    
    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化仓库
        
        Args:
            db_manager: 数据库管理器
        """
        if self.TABLE_NAME is None:
            raise NotImplementedError("子类必须定义 TABLE_NAME")
        
        self.db = db_manager or get_db_manager()
        self.logger = get_logger(f"repository.{self.full_table_name}")
        self._table_ready = False
        self._known_columns: Set[str] = set()
        self._fields_cache: Optional[Dict[str, str]] = None
    
    @property
    def full_table_name(self) -> str:
        """完整表名（带系统前缀）"""
        if self.SYSTEM_PREFIX:
            return f"{self.SYSTEM_PREFIX}_{self.TABLE_NAME}"
        return self.TABLE_NAME
    
    def save_batch(self, data_list: List[Dict], batch_size: int = 500, debug: bool = False, progress_label: str = '') -> int:
        if not data_list:
            return 0
        
        total = len(data_list)
        table_name = self.full_table_name
        
        try:
            fields = self._analyze_fields(data_list)
            if not self._table_ready:
                self._ensure_table(fields)
                self._table_ready = True
            self._ensure_columns(fields)
        except Exception as e:
            self.logger.error(f"表结构初始化失败: {e}")
            print(f"    [ERROR] 表结构初始化失败 ({self.full_table_name}): {e}", flush=True)
            raise
        
        is_mysql = self.db.adapter.__class__.__name__ == 'MySQLAdapter'
        col_names = [sanitize_column_name(f) for f in fields.keys()]
        
        if self.UNIQUE_KEY:
            if isinstance(self.UNIQUE_KEY, (list, tuple)):
                unique_key = [sanitize_column_name(k) for k in self.UNIQUE_KEY]
            else:
                unique_key = [sanitize_column_name(self.UNIQUE_KEY)]
        else:
            unique_key = None
        
        if not is_mysql and unique_key:
            return self._save_batch_sqlserver_merge(data_list, fields, col_names, unique_key, batch_size, debug=debug, progress_label=progress_label)
        
        count = 0
        errors = 0
        sql = self.db.adapter.upsert_sql(table_name, col_names, unique_key[0] if unique_key and len(unique_key) == 1 else unique_key)
        label = progress_label or table_name
        milestones = {int(total * p) for p in (0.25, 0.5, 0.75)} if total >= 4 else set()
        
        with self.db.get_connection() as conn:
            cursor = self.db.adapter.get_cursor(conn)
            
            for batch_start in range(0, total, batch_size):
                batch_end = min(batch_start + batch_size, total)
                batch = data_list[batch_start:batch_end]
                
                batch_data = []
                for item in batch:
                    if is_mysql:
                        row = {}
                        for field_name in fields.keys():
                            col_name = sanitize_column_name(field_name)
                            value = item.get(field_name)
                            if isinstance(value, (list, dict)):
                                value = json.dumps(value, ensure_ascii=False)
                            row[col_name] = value
                        batch_data.append(row)
                    else:
                        row = []
                        for field_name, field_type in fields.items():
                            value = item.get(field_name)
                            value = self._coerce_value(value, field_type)
                            row.append(value)
                        batch_data.append(tuple(row))
                
                try:
                    cursor.executemany(sql, batch_data)
                    count += len(batch_data)
                    if debug and (batch_end == total or any(m and abs(batch_end - m) < batch_size for m in milestones)):
                        pct = int(batch_end * 100 / total) if total else 100
                        debug_print(f"  [SAVE] {label} {batch_end:,}/{total:,} ({pct}%)")
                except Exception as e:
                    errors += len(batch_data)
                    self.logger.error(f"批量保存失败: {e}")
                    self.logger.error(f"SQL: {sql[:200]}...")
                    self.logger.error(f"参数示例: {batch_data[0] if batch_data else 'None'}")
                    print(f"    [ERROR] 批量保存失败 ({table_name}): {e}", flush=True)
                
                self.db.adapter.commit(conn)
        
        if errors > 0:
            self.logger.warning(f"保存 {table_name}: 成功 {count} 条，失败 {errors} 条")
        else:
            self.logger.info(f"保存 {table_name}: {count} 条")
        
        return count
    
    @staticmethod
    def _coerce_value(value, field_type):
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, str) and field_type in ('BIGINT', 'BIT', 'DECIMAL(19,4)'):
            if value == '':
                return None
            try:
                if field_type == 'BIGINT':
                    return int(value)
                elif field_type == 'DECIMAL(19,4)':
                    return float(value)
            except (ValueError, TypeError):
                return None
        return value
    
    def _save_batch_sqlserver_merge(self, data_list: List[Dict], fields: Dict, col_names: List[str], unique_key: List[str], batch_size: int, max_retries: int = 3, debug: bool = False, progress_label: str = '') -> int:
        import time
        import threading

        table_name = self.full_table_name
        tid = threading.current_thread().ident
        temp_table = f"#tmp_{self.TABLE_NAME}_{tid}"
        total = len(data_list)
        label = progress_label or table_name

        col_defs_full = ', '.join([f'[{c}] NVARCHAR(MAX)' for c in col_names])

        insert_cols = ', '.join([f'[{c}]' for c in col_names])
        placeholders = ', '.join(['?' for _ in col_names])
        insert_sql = f"INSERT INTO [{temp_table}] ({insert_cols}) VALUES ({placeholders})"

        source_vals = ', '.join([f'source.[{c}]' for c in col_names])
        on_clause = ' AND '.join([f'target.[{k}] = source.[{k}]' for k in unique_key])
        update_set = ', '.join([f'target.[{c}] = source.[{c}]' for c in col_names if c not in unique_key])

        cast_parts = []
        target_types = list(fields.values())
        for i, c in enumerate(col_names):
            tgt_type = target_types[i]
            if tgt_type != 'NVARCHAR(MAX)':
                cast_parts.append(f'TRY_CAST(source.[{c}] AS {tgt_type}) AS [{c}]')
            else:
                cast_parts.append(f'source.[{c}]')
        cast_select = ', '.join(cast_parts)

        merge_sql = f"""
            MERGE INTO [{table_name}] WITH (HOLDLOCK) AS target
            USING (SELECT {cast_select} FROM [{temp_table}] AS source) AS source
            ON {on_clause}
            WHEN MATCHED THEN
                UPDATE SET {update_set}
            WHEN NOT MATCHED THEN
                INSERT ({insert_cols})
                VALUES ({source_vals});
        """
        milestones = {int(total * p) for p in (0.25, 0.5, 0.75)} if total >= 4 else set()

        for attempt in range(1, max_retries + 1):
            count = 0
            errors = 0

            with self.db.get_connection() as conn:
                cursor = self.db.adapter.get_cursor(conn)

                try:
                    cursor.execute(f"IF OBJECT_ID('tempdb..{temp_table}') IS NOT NULL DROP TABLE [{temp_table}]")
                    cursor.execute(f"CREATE TABLE [{temp_table}] ({col_defs_full})")
                    self.db.adapter.commit(conn)

                    import pyodbc
                    input_sizes = [(pyodbc.SQL_WVARCHAR, 0, 0)] * len(col_names)

                    for batch_start in range(0, total, batch_size):
                        batch_end = min(batch_start + batch_size, total)
                        batch = data_list[batch_start:batch_end]

                        batch_data = []
                        for item in batch:
                            row = []
                            for field_name in fields.keys():
                                value = item.get(field_name)
                                if isinstance(value, bool):
                                    value = str(int(value))
                                elif isinstance(value, (int, float)):
                                    value = str(value)
                                elif isinstance(value, (list, dict)):
                                    value = json.dumps(value, ensure_ascii=False)
                                row.append(value)
                            batch_data.append(tuple(row))

                        cursor.setinputsizes(input_sizes)
                        cursor.executemany(insert_sql, batch_data)
                        count += len(batch_data)
                        if debug and (batch_end == total or any(m and abs(batch_end - m) < batch_size for m in milestones)):
                            pct = int(batch_end * 100 / total) if total else 100
                            debug_print(f"  [SAVE] {label} {batch_end:,}/{total:,} ({pct}%)")

                    self.db.adapter.commit(conn)

                    uk_cols = ', '.join([f'[{k}]' for k in unique_key])
                    dedup_sql = f"""
                        ;WITH CTE AS (
                            SELECT *, ROW_NUMBER() OVER (PARTITION BY {uk_cols} ORDER BY (SELECT NULL)) AS _rn
                            FROM [{temp_table}]
                        )
                        DELETE FROM CTE WHERE _rn > 1
                    """
                    cursor.execute(dedup_sql)
                    self.db.adapter.commit(conn)

                    cursor.execute(merge_sql)
                    self.db.adapter.commit(conn)

                    cursor.execute(f"DROP TABLE [{temp_table}]")
                    self.db.adapter.commit(conn)

                except Exception as e:
                    errors = total
                    count = 0
                    try:
                        cursor.execute(f"IF OBJECT_ID('tempdb..{temp_table}') IS NOT NULL DROP TABLE [{temp_table}]")
                        self.db.adapter.commit(conn)
                    except:
                        pass

                    err_code = getattr(e, 'args', [None])[0] if hasattr(e, 'args') and e.args else None
                    is_retryable = str(err_code) in ('40001', '23000')

                    if is_retryable and attempt < max_retries:
                        wait = attempt * 2
                        self.logger.warning(f"批量保存冲突(第{attempt}次)，{wait}秒后重试: {e}")
                        time.sleep(wait)
                        continue
                    else:
                        self.logger.error(f"批量保存失败: {e}")
                        print(f"    [ERROR] 批量保存失败 ({table_name}): {e}", flush=True)

            if errors > 0:
                self.logger.warning(f"保存 {table_name}: 成功 {count} 条，失败 {errors} 条")
            else:
                self.logger.info(f"保存 {table_name}: {count} 条")

            return count

        return 0
    
    def _default_string_column_type(self) -> str:
        db_type = self.db.config.database.type
        return 'NVARCHAR(MAX)' if db_type.lower() == 'sqlserver' else 'TEXT'

    def _analyze_fields(self, data_list: List[Dict], sample_size: int = 100) -> Dict[str, str]:
        """分析数据字段和类型（全量 key 并集 + 预留列，类型从前 sample_size 条推断）"""
        db_type = self.db.config.database.type
        default_str = self._default_string_column_type()

        if self._fields_cache is None:
            fields: Dict[str, str] = {}
        else:
            fields = dict(self._fields_cache)

        new_keys = False
        pending_type: Set[str] = set()

        reserved = getattr(type(self), 'RESERVED_COLUMNS', None) or {}
        for key, col_type in reserved.items():
            if key not in fields:
                fields[key] = col_type
                new_keys = True

        for item in data_list:
            for key in item.keys():
                if key not in fields:
                    fields[key] = default_str
                    pending_type.add(key)
                    new_keys = True

        for item in data_list[:sample_size]:
            for key, value in item.items():
                if value is None:
                    continue
                new_type = infer_column_type(value, db_type)
                if key in pending_type:
                    fields[key] = new_type
                    pending_type.discard(key)
                    new_keys = True
                elif key not in fields:
                    fields[key] = new_type
                    new_keys = True
                else:
                    current_type = fields[key]
                    if current_type in ('TEXT', 'NVARCHAR(MAX)') and new_type not in ('TEXT', 'NVARCHAR(MAX)'):
                        fields[key] = new_type
                        new_keys = True

        for key in pending_type:
            resolved = None
            for item in data_list:
                val = item.get(key)
                if val is not None:
                    resolved = infer_column_type(val, db_type)
                    break
            fields[key] = resolved or default_str
            new_keys = True

        if self._fields_cache is None or new_keys:
            self._fields_cache = fields

        return fields
    
    def _ensure_table(self, fields: Dict[str, str]):
        """确保表存在"""
        table_name = self.full_table_name
        
        columns = []
        for field_name, field_type in fields.items():
            col_name = sanitize_column_name(field_name)
            columns.append((col_name, field_type))
        
        if self.UNIQUE_KEY:
            if isinstance(self.UNIQUE_KEY, (list, tuple)):
                unique_col = [sanitize_column_name(k) for k in self.UNIQUE_KEY]
            else:
                unique_col = sanitize_column_name(self.UNIQUE_KEY)
        else:
            unique_col = None
        pk_col = getattr(self, 'SQLSERVER_PRIMARY_KEY', None)
        create_sql = self.db.adapter.build_create_table_sql(
            table_name, columns, unique_col, sqlserver_pk_column=pk_col
        )
        
        with self.db.get_connection() as conn:
            cursor = self.db.adapter.get_cursor(conn)
            cursor.execute(create_sql)
            self.db.adapter.commit(conn)
        
        if unique_col and hasattr(self.db.adapter, 'build_unique_constraint_sql'):
            try:
                uk_sql = self.db.adapter.build_unique_constraint_sql(table_name, unique_col)
                with self.db.get_connection() as conn:
                    cursor = self.db.adapter.get_cursor(conn)
                    cursor.execute(uk_sql)
                    self.db.adapter.commit(conn)
            except Exception:
                pass
    
    def _ensure_columns(self, fields: Dict[str, str]):
        """确保所有列存在（带实例级缓存，避免每次保存都查所有列）"""
        table_name = self.full_table_name
        
        target_cols = {sanitize_column_name(f): t for f, t in fields.items()}
        
        if self._known_columns and all(c in self._known_columns for c in target_cols):
            return
        
        try:
            existing = set(c.lower() for c in self.db.get_table_columns(table_name))
            self._known_columns = set(existing)
        except Exception as e:
            self.logger.error(f"获取表列失败: {e}")
            existing = set(self._known_columns)
        
        missing = [(c, t) for c, t in target_cols.items() if c.lower() not in existing]
        if not missing:
            self._known_columns.update(target_cols.keys())
            return
        
        is_mysql = self.db.adapter.__class__.__name__ == 'MySQLAdapter'
        with self.db.get_connection() as conn:
            cursor = self.db.adapter.get_cursor(conn)
            added = 0
            for col_name, field_type in missing:
                try:
                    if is_mysql:
                        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {field_type}")
                    else:
                        cursor.execute(f"ALTER TABLE [{table_name}] ADD [{col_name}] {field_type}")
                    added += 1
                    self._known_columns.add(col_name.lower())
                except Exception:
                    pass
            
            if added > 0:
                self.db.adapter.commit(conn)
                self.logger.info(f"新增 {added} 个字段到表 {table_name}")
        
        self._known_columns.update(c.lower() for c in target_cols)
    
    def find_by_id(self, unique_value: Any) -> Optional[Dict]:
        """根据唯一键查询"""
        if not self.UNIQUE_KEY:
            raise ValueError("未定义 UNIQUE_KEY")
        
        col_name = sanitize_column_name(self.UNIQUE_KEY)
        table_name = self.full_table_name
        
        if self.db.adapter.__class__.__name__ == 'MySQLAdapter':
            sql = f"SELECT * FROM `{table_name}` WHERE `{col_name}` = %s LIMIT 1"
        else:  # SQL Server
            sql = f"SELECT TOP 1 * FROM [{table_name}] WHERE [{col_name}] = ?"
        
        return self.db.fetch_one(sql, (unique_value,))
    
    def count(self, where: str = None, params: tuple = None) -> int:
        """统计数量"""
        table_name = self.full_table_name
        
        if self.db.adapter.__class__.__name__ == 'MySQLAdapter':
            sql = f"SELECT COUNT(*) as cnt FROM `{table_name}`"
        else:  # SQL Server
            sql = f"SELECT COUNT(*) as cnt FROM [{table_name}]"
        
        if where:
            sql += f" WHERE {where}"
        result = self.db.fetch_one(sql, params)
        return result['cnt'] if result else 0
    
    def delete_by_time_range(self, time_field: str, start_time: str, end_time: str) -> int:
        """按时间范围删除"""
        col_name = sanitize_column_name(time_field)
        table_name = self.full_table_name
        
        if self.db.adapter.__class__.__name__ == 'MySQLAdapter':
            sql = f"DELETE FROM `{table_name}` WHERE `{col_name}` >= %s AND `{col_name}` <= %s"
        else:  # SQL Server
            sql = f"DELETE FROM [{table_name}] WHERE [{col_name}] >= ? AND [{col_name}] <= ?"
        
        return self.db.execute(sql, (start_time, end_time))
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(table={self.full_table_name})>"

