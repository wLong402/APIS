# -*- coding: utf-8 -*-
"""
客户数据仓库

实现特殊的存储逻辑：
- 新增数据：添加 join_time（加入时间）
- 流失数据：更新 outflow_time（流失时间）
"""

import json
from datetime import datetime, date
from typing import Dict, List, Any, Set, Optional

from core.database import (
    DatabaseManager, get_db_manager,
    sanitize_column_name, infer_column_type
)
from core.logger import get_logger


class ExternalUserRepository:
    """
    客户数据仓库
    
    实现特殊的数据对比存储逻辑：
    1. 今天拉取的数据和前一日数据对比（按客户ID）
    2. 如果昨天存在今天不存在 → 更新该数据的 outflow_time 为今天
    3. 如果数据库不存在今天存在 → 将今天日期作为 join_time 存入
    
    表结构会自动添加两个额外字段：
    - join_time: 加入时间（首次拉取到该客户的日期）
    - outflow_time: 流失时间（客户流失的日期，NULL 表示未流失）
    """
    
    TABLE_NAME = 'external_user'
    UNIQUE_KEY = 'id'  # external_id 作为唯一键
    SYSTEM_PREFIX = 'weiban'
    COMPOSITE_UNIQUE_KEY = ('id', 'staff_id')
    
    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化仓库
        
        Args:
            db_manager: 数据库管理器
        """
        self.db = db_manager or get_db_manager()
        self.logger = get_logger(f"repository.{self.full_table_name}")
        self._adapter = self.db.adapter
        self._is_mysql = self._adapter.__class__.__name__ == 'MySQLAdapter'
        self._q = self._adapter.quote
        self._ph = '%s' if self._is_mysql else '?'
    
    @property
    def full_table_name(self) -> str:
        """完整表名（带系统前缀）"""
        return f"{self.SYSTEM_PREFIX}_{self.TABLE_NAME}"
    
    def save_with_comparison(self, data_list: List[Dict], 
                              compare_date: date = None,
                              batch_size: int = 500,
                              debug: bool = False) -> Dict[str, int]:
        """
        带对比的批量保存
        
        实现特殊逻辑：
        1. 获取前一日的所有客户ID
        2. 对比今天拉取的数据
        3. 新增客户：设置 join_time
        4. 流失客户：更新 outflow_time
        
        Args:
            data_list: 今日拉取的客户数据列表
            compare_date: 对比日期（默认为今天）
            batch_size: 批量大小
            debug: 是否打印调试信息
            
        Returns:
            操作统计:
                - saved: 保存的数量
                - new_joined: 新加入的客户数
                - outflow_marked: 标记流失的客户数
        """
        from core.logger import debug_print
        
        if not data_list:
            return {'saved': 0, 'new_joined': 0, 'outflow_marked': 0}
        
        today = compare_date or date.today()
        today_str = today.strftime('%Y-%m-%d')
        
        if debug:
            debug_print(f"    开始处理 {len(data_list)} 条客户数据，对比日期: {today_str}")
        
        self.logger.info(f"开始处理 {len(data_list)} 条客户数据，对比日期: {today_str}")
        
        # 1. 扁平化数据（将 staff_relation 展开）
        flat_data = self._flatten_data(data_list)
        
        # 2. 分析字段并确保表结构
        fields = self._analyze_fields(flat_data)
        # 强制 id 和 staff_id 使用 VARCHAR(255)，否则无法创建唯一索引
        fields['id'] = 'VARCHAR(255)'
        fields['staff_id'] = 'VARCHAR(255)'
        # 添加额外字段
        fields['join_time'] = 'DATE'
        fields['outflow_time'] = 'DATE'
        fields['last_pull_date'] = 'DATE'  # 最后拉取日期，用于判断是否流失
        
        self._ensure_table(fields)
        self._ensure_columns(fields)
        
        # 3. 获取数据库中所有客户的复合键和流失状态（用于对比）
        existing_info = self._get_existing_user_info()
        existing_keys = set(existing_info.keys())
        outflow_keys = {key for key, info in existing_info.items() if info.get('outflow_time')}
        
        # 4. 今日拉取的客户复合键集合
        today_keys = {self._make_composite_key(item) for item in flat_data if item.get('id')}
        
        # 5. 计算新加入和流失的客户
        new_joined_keys = today_keys - existing_keys
        # 流失客户：数据库中存在但今天没有拉取到，且还没有被标记为流失
        potential_outflow_keys = existing_keys - today_keys - outflow_keys
        
        if debug:
            debug_print(f"    数据库现有客户: {len(existing_keys)} 条")
            debug_print(f"    今日拉取客户: {len(today_keys)} 条")
            debug_print(f"    新加入: {len(new_joined_keys)} 条")
            debug_print(f"    可能流失: {len(potential_outflow_keys)} 条")
            debug_print(f"    已流失客户: {len(outflow_keys)} 条")
            
            # 调试：显示一些示例复合键
            if existing_keys and today_keys:
                sample_existing = list(existing_keys)[:3]
                sample_today = list(today_keys)[:3]
                debug_print(f"    数据库示例复合键: {sample_existing}")
                debug_print(f"    今日示例复合键: {sample_today}")
                debug_print(f"    交集数量: {len(existing_keys & today_keys)}")
                if new_joined_keys:
                    sample_new = list(new_joined_keys)[:5]
                    debug_print(f"    新加入示例复合键: {sample_new}")
        
        self.logger.info(f"新加入: {len(new_joined_keys)} 条，可能流失: {len(potential_outflow_keys)} 条")
        if len(new_joined_keys) > len(today_keys) * 0.5:
            self.logger.warning(f"警告: 新加入数量({len(new_joined_keys)})超过今日拉取数量({len(today_keys)})的50%，可能存在复合键对比问题")
        
        # 6. 分离新加入和已存在的客户（按复合键去重，保留最后一条）
        new_items = []
        update_items = []
        return_items = []
        seen_keys = set()
        
        for item in reversed(flat_data):
            composite_key = self._make_composite_key(item)
            if not composite_key or composite_key in seen_keys:
                continue
            seen_keys.add(composite_key)
                
            if composite_key in new_joined_keys:
                item['join_time'] = today_str
                item['last_pull_date'] = today_str
                new_items.append(item)
            elif composite_key in outflow_keys:
                item['outflow_time'] = None
                item['last_pull_date'] = today_str
                return_items.append(item)
            elif composite_key in existing_keys:
                item['last_pull_date'] = today_str
                update_items.append(item)
        
        # 7. 插入新加入的客户
        new_count = 0
        if new_items:
            if debug:
                debug_print(f"    开始插入新加入客户: {len(new_items)} 条...")
            new_count = self._insert_batch(new_items, fields, batch_size, debug=debug)
            if debug:
                debug_print(f"    ✓ 新加入客户插入完成: {new_count} 条")
        
        # 8. 更新已存在的客户
        update_count = 0
        if update_items:
            if debug:
                # 先检查数据库当前记录数
                check_sql = f"SELECT COUNT(*) as cnt FROM {self._q(self.full_table_name)}"
                before_count = self.db.fetch_one(check_sql)
                debug_print(f"    更新前数据库记录数: {before_count['cnt'] if before_count else 0}")
                debug_print(f"    开始更新已存在客户: {len(update_items)} 条...")
            
            update_count = self._update_batch(update_items, fields, batch_size, debug=debug)
            
            if debug:
                # 检查更新后数据库记录数
                after_count = self.db.fetch_one(check_sql)
                actual_new = (after_count['cnt'] if after_count else 0) - (before_count['cnt'] if before_count else 0)
                if actual_new > len(update_items) * 0.1:
                    self.logger.error(f"错误: 更新操作导致数据库新增 {actual_new} 条记录，说明唯一索引可能失效！")
                    debug_print(f"    ⚠ 警告: 更新操作导致数据库新增 {actual_new} 条记录")
                debug_print(f"    更新后数据库记录数: {after_count['cnt'] if after_count else 0}")
                debug_print(f"    ✓ 已存在客户更新完成: {update_count} 条")
        
        # 9. 处理重新回来的客户（清除流失标记）
        return_count = 0
        if return_items:
            if debug:
                debug_print(f"    开始处理重新回来客户: {len(return_items)} 条...")
            return_count = self._update_batch(return_items, fields, batch_size, debug=debug)
            if debug:
                debug_print(f"    ✓ 重新回来客户处理完成: {return_count} 条")
        
        saved_count = new_count + update_count + return_count
        
        # 10. 标记流失客户（数据库中存在但今天没有拉取到的，且未流失的）
        if debug and potential_outflow_keys:
            debug_print(f"    开始标记流失客户...")
        
        outflow_count = self._mark_outflow(potential_outflow_keys, today_str)
        
        if debug and return_count > 0:
            debug_print(f"    重新回来: {return_count} 条")
        
        result = {
            'saved': saved_count,
            'new_joined': len(new_joined_keys),
            'outflow_marked': outflow_count
        }
        
        if debug:
            debug_print(f"    处理完成:")
            debug_print(f"      - 实际新增: {new_count} 条")
            debug_print(f"      - 实际更新: {update_count} 条")
            debug_print(f"      - 重新回来: {return_count} 条")
            debug_print(f"      - 总计处理: {saved_count} 条")
            debug_print(f"      - 标记流失: {outflow_count} 条")
        
        self.logger.info(f"处理完成: 新增 {new_count} 条，更新 {update_count} 条，重新回来 {return_count} 条，标记流失 {outflow_count} 条")
        
        return result
    
    
    def _make_composite_key(self, item: Dict) -> str:
        """
        生成复合唯一键
        
        Args:
            item: 数据项
            
        Returns:
            复合键字符串 (id_staff_id)
        """
        user_id = str(item.get('id', '')).strip()
        staff_id = str(item.get('staff_id', '')).strip()
        if not user_id:
            return ''
        return f"{user_id}_{staff_id}"
    
    def _flatten_data(self, data_list: List[Dict]) -> List[Dict]:
        """
        扁平化数据（将 staff_relation 展开到主记录）
        
        Args:
            data_list: 原始数据列表
            
        Returns:
            扁平化后的数据列表
        """
        flat_list = []
        
        for item in data_list:
            flat_item = {}
            
            # 复制主要字段
            for key, value in item.items():
                if key == 'staff_relation' and isinstance(value, dict):
                    # 展开 staff_relation
                    for sub_key, sub_value in value.items():
                        flat_item[f'staff_{sub_key}' if sub_key != 'staff_id' else sub_key] = sub_value
                elif key == 'external_profile':
                    # external_profile 可能是复杂对象，转为 JSON
                    if isinstance(value, (dict, list)):
                        flat_item[key] = json.dumps(value, ensure_ascii=False)
                    else:
                        flat_item[key] = value
                else:
                    flat_item[key] = value
            
            flat_list.append(flat_item)
        
        return flat_list
    
    def _get_existing_user_info(self) -> Dict[str, Dict]:
        """
        获取数据库中所有客户的信息（包括流失状态）
        
        Returns:
            客户信息字典，key为复合键(id_staff_id)，value为包含outflow_time的字典
        """
        table_name = self.full_table_name
        if not self.db.table_exists(table_name):
            return {}
        sql = f"SELECT {self._q('id')}, {self._q('staff_id')}, {self._q('outflow_time')} FROM {self._q(table_name)}"
        try:
            rows = self.db.fetch_all(sql)
            # 生成复合键作为key
            result_dict = {}
            for row in rows:
                user_id = str(row.get('id', '')).strip()
                staff_id = str(row.get('staff_id', '')).strip()
                if user_id:
                    composite_key = f"{user_id}_{staff_id}"
                    result_dict[composite_key] = {'outflow_time': row.get('outflow_time')}
            return result_dict
        except Exception as e:
            self.logger.warning(f"获取现有客户信息失败: {e}")
            return {}
    
    def _mark_outflow(self, outflow_keys: Set[str], outflow_date: str) -> int:
        if not outflow_keys:
            return 0
        table_name = self.full_table_name
        count = 0
        q, ph = self._q, self._ph
        with self.db.get_connection() as conn:
            cursor = self._adapter.get_cursor(conn)
            for composite_key in outflow_keys:
                try:
                    parts = composite_key.split('_', 1)
                    user_id = parts[0]
                    staff_id = parts[1] if len(parts) > 1 else ''
                    sql = f"UPDATE {q(table_name)} SET {q('outflow_time')} = {ph} WHERE {q('id')} = {ph} AND {q('staff_id')} = {ph} AND {q('outflow_time')} IS NULL"
                    cursor.execute(sql, (outflow_date, user_id, staff_id))
                    count += cursor.rowcount
                except Exception as e:
                    self.logger.error(f"标记流失失败 {composite_key}: {e}")
            self._adapter.commit(conn)
        return count
    
    def _analyze_fields(self, data_list: List[Dict], sample_size: int = 100) -> Dict[str, str]:
        """分析数据字段和类型"""
        db_type = self.db.config.database.type
        fields = {}
        for item in data_list[:sample_size]:
            for key, value in item.items():
                if key not in fields:
                    fields[key] = infer_column_type(value, db_type)
                elif value is not None and fields[key] in ('TEXT', 'NVARCHAR(MAX)'):
                    new_type = infer_column_type(value, db_type)
                    if new_type not in ('TEXT', 'NVARCHAR(MAX)'):
                        fields[key] = new_type
        return fields
    
    def _ensure_table(self, fields: Dict[str, str]):
        table_name = self.full_table_name
        q = self._q
        with self.db.get_connection() as conn:
            cursor = self._adapter.get_cursor(conn)
            if self._is_mysql:
                columns = ['pk_id INT AUTO_INCREMENT PRIMARY KEY']
                for field_name, field_type in fields.items():
                    col_name = sanitize_column_name(field_name)
                    if col_name.lower() not in ('created_at', 'updated_at'):
                        columns.append(f'{q(col_name)} {field_type}')
                if 'created_at' not in [sanitize_column_name(f).lower() for f in fields.keys()]:
                    columns.append('created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
                if 'updated_at' not in [sanitize_column_name(f).lower() for f in fields.keys()]:
                    columns.append('updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')
                create_sql = f"CREATE TABLE IF NOT EXISTS {q(table_name)} ({', '.join(columns)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC"
                cursor.execute(create_sql)
                index_name = 'idx_user_staff'
                db_name = getattr(self.db.db_config, 'database', '')
                cursor.execute(f"SELECT COUNT(*) as cnt FROM information_schema.statistics WHERE table_schema = %s AND table_name = %s AND index_name = %s", (db_name, table_name, index_name))
                result = cursor.fetchone()
                if not (result and (result.get('cnt') or result[0]) > 0):
                    try:
                        try:
                            cursor.execute(f"ALTER TABLE {q(table_name)} MODIFY COLUMN {q('id')} VARCHAR(255)")
                            cursor.execute(f"ALTER TABLE {q(table_name)} MODIFY COLUMN {q('staff_id')} VARCHAR(255)")
                            self._adapter.commit(conn)
                        except Exception:
                            pass
                        cursor.execute(f"DELETE t1 FROM {q(table_name)} t1 INNER JOIN {q(table_name)} t2 WHERE t1.{q('id')}=t2.{q('id')} AND t1.{q('staff_id')}=t2.{q('staff_id')} AND t1.{q('pk_id')}<t2.{q('pk_id')}")
                        self._adapter.commit(conn)
                        cursor.execute(f"ALTER TABLE {q(table_name)} ADD UNIQUE INDEX {q(index_name)} ({q('id')}, {q('staff_id')})")
                        self._adapter.commit(conn)
                    except Exception as e:
                        self.logger.warning(f"添加复合唯一索引失败: {e}")
            else:
                if not self.db.table_exists(table_name):
                    col_defs = ['[pk_id] BIGINT IDENTITY(1,1) PRIMARY KEY']
                    for field_name, field_type in fields.items():
                        col_name = sanitize_column_name(field_name)
                        if col_name.lower() not in ('created_at', 'updated_at'):
                            col_defs.append(f'[{col_name}] {field_type}')
                    col_defs.append('[created_at] DATETIME DEFAULT GETDATE()')
                    col_defs.append('[updated_at] DATETIME DEFAULT GETDATE()')
                    create_sql = f"CREATE TABLE [{table_name}] ({', '.join(col_defs)})"
                    cursor.execute(create_sql)
                    self._adapter.commit(conn)
                try:
                    uk_sql = self._adapter.build_unique_constraint_sql(table_name, ['id', 'staff_id'])
                    cursor.execute(uk_sql)
                    self._adapter.commit(conn)
                except Exception:
                    pass
            self._adapter.commit(conn)
    
    def _ensure_columns(self, fields: Dict[str, str]):
        table_name = self.full_table_name
        q = self._q
        existing = set(self.db.get_table_columns(table_name))
        with self.db.get_connection() as conn:
            cursor = self._adapter.get_cursor(conn)
            added = 0
            for field_name, field_type in fields.items():
                col_name = sanitize_column_name(field_name)
                if col_name.lower() not in existing and col_name.lower() not in ('created_at', 'updated_at'):
                    try:
                        cursor.execute(f"ALTER TABLE {q(table_name)} ADD COLUMN {q(col_name)} {field_type}")
                        added += 1
                    except Exception:
                        pass
            if 'created_at' not in existing:
                try:
                    dt_def = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP" if self._is_mysql else "DATETIME DEFAULT GETDATE()"
                    cursor.execute(f"ALTER TABLE {q(table_name)} ADD COLUMN {q('created_at')} {dt_def}")
                    added += 1
                except Exception:
                    pass
            if 'updated_at' not in existing:
                try:
                    dt_def = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP" if self._is_mysql else "DATETIME DEFAULT GETDATE()"
                    cursor.execute(f"ALTER TABLE {q(table_name)} ADD COLUMN {q('updated_at')} {dt_def}")
                    added += 1
                except Exception:
                    pass
            if added > 0:
                self._adapter.commit(conn)
                self.logger.info(f"新增 {added} 个字段到表 {table_name}")
    
    def _insert_batch(self, data_list: List[Dict], fields: Dict[str, str], 
                     batch_size: int = 500, debug: bool = False) -> int:
        if not data_list:
            return 0
        from core.logger import debug_print
        total = len(data_list)
        table_name = self.full_table_name
        count = 0
        total_batches = (total + batch_size - 1) // batch_size
        q, ph = self._q, self._ph
        system_fields = {'created_at', 'updated_at'}
        col_names = [sanitize_column_name(f) for f in fields.keys() 
                    if sanitize_column_name(f).lower() not in system_fields]
        if self._is_mysql:
            placeholders = ', '.join([f'%({c})s' for c in col_names])
            sql = f"INSERT INTO {q(table_name)} ({', '.join([q(c) for c in col_names])}) VALUES ({placeholders})"
        else:
            placeholders = ', '.join([ph] * len(col_names))
            sql = f"INSERT INTO {q(table_name)} ({', '.join([q(c) for c in col_names])}) VALUES ({placeholders})"
        with self.db.get_connection() as conn:
            cursor = self._adapter.get_cursor(conn)
            for batch_idx, batch_start in enumerate(range(0, total, batch_size), 1):
                batch_end = min(batch_start + batch_size, total)
                batch = data_list[batch_start:batch_end]
                batch_data = []
                for item in batch:
                    if self._is_mysql:
                        row = {}
                        for field_name in fields.keys():
                            col_name = sanitize_column_name(field_name)
                            if col_name.lower() not in system_fields:
                                value = item.get(field_name)
                                if isinstance(value, (list, dict)):
                                    value = json.dumps(value, ensure_ascii=False)
                                row[col_name] = value
                        batch_data.append(row)
                    else:
                        row = []
                        for field_name in fields.keys():
                            col_name = sanitize_column_name(field_name)
                            if col_name.lower() not in system_fields:
                                value = item.get(field_name)
                                if isinstance(value, (list, dict)):
                                    value = json.dumps(value, ensure_ascii=False)
                                row.append(value)
                        batch_data.append(tuple(row))
                try:
                    cursor.executemany(sql, batch_data)
                    count += len(batch_data)
                    self._adapter.commit(conn)
                    if debug and batch_idx % 10 == 0:
                        debug_print(f"    插入进度: {batch_idx}/{total_batches} 批 ({count}/{total} 条)")
                except Exception as e:
                    self.logger.error(f"批量插入失败: {e}")
                    self._adapter.rollback(conn)
        return count
    
    def _update_batch(self, data_list: List[Dict], fields: Dict[str, str], 
                     batch_size: int = 500, debug: bool = False) -> int:
        if not data_list:
            return 0
        from core.logger import debug_print
        import threading
        total = len(data_list)
        table_name = self.full_table_name
        count = 0
        q, ph = self._q, self._ph
        system_fields = {'created_at', 'updated_at'}
        col_names = [sanitize_column_name(f) for f in fields.keys() 
                    if sanitize_column_name(f).lower() not in system_fields]
        if 'id' in col_names:
            col_names.remove('id')
        if 'staff_id' in col_names:
            col_names.remove('staff_id')
        col_names.insert(0, 'id')
        col_names.insert(1, 'staff_id')
        update_cols = [col for col in col_names if col not in ('id', 'staff_id', 'join_time')]
        if self._is_mysql:
            update_parts = ', '.join([f'{q(col)} = VALUES({q(col)})' for col in update_cols])
            placeholders = ', '.join([f'%({c})s' for c in col_names])
            sql = f"INSERT INTO {q(table_name)} ({', '.join([q(c) for c in col_names])}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_parts}"
            with self.db.get_connection() as conn:
                cursor = self._adapter.get_cursor(conn)
                for batch_idx, batch_start in enumerate(range(0, total, batch_size), 1):
                    batch_end = min(batch_start + batch_size, total)
                    batch = data_list[batch_start:batch_end]
                    batch_data = []
                    for item in batch:
                        user_id = str(item.get('id', '')).strip()
                        staff_id = str(item.get('staff_id', '')).strip()
                        if not user_id:
                            continue
                        row = {'id': user_id, 'staff_id': staff_id}
                        for field_name in fields.keys():
                            col_name = sanitize_column_name(field_name)
                            if col_name.lower() not in system_fields and col_name not in ('id', 'staff_id'):
                                value = item.get(field_name)
                                if isinstance(value, (list, dict)):
                                    value = json.dumps(value, ensure_ascii=False)
                                row[col_name] = value
                        batch_data.append(row)
                    try:
                        cursor.executemany(sql, batch_data)
                        count += len(batch_data)
                        self._adapter.commit(conn)
                        if debug and batch_idx % 10 == 0:
                            debug_print(f"    更新进度: {batch_idx} 批 ({count}/{total} 条)")
                    except Exception as e:
                        self.logger.error(f"批量更新失败: {e}")
                        self._adapter.rollback(conn)
        else:
            tid = threading.current_thread().ident
            temp_table = f"#tmp_ext_{tid}"
            with self.db.get_connection() as conn:
                cursor = self._adapter.get_cursor(conn)
                col_defs = ', '.join([f'[{c}] NVARCHAR(MAX)' for c in col_names])
                cursor.execute(f"IF OBJECT_ID('tempdb..{temp_table}') IS NOT NULL DROP TABLE [{temp_table}]")
                cursor.execute(f"CREATE TABLE [{temp_table}] ({col_defs})")
                self._adapter.commit(conn)
                insert_cols = ', '.join([f'[{c}]' for c in col_names])
                placeholders = ', '.join(['?'] * len(col_names))
                insert_sql = f"INSERT INTO [{temp_table}] ({insert_cols}) VALUES ({placeholders})"
                for batch_start in range(0, total, batch_size):
                    batch_end = min(batch_start + batch_size, total)
                    batch = data_list[batch_start:batch_end]
                    col_to_field = {sanitize_column_name(f): f for f in fields.keys()}
                    batch_data = []
                    for item in batch:
                        user_id = str(item.get('id', '')).strip()
                        staff_id = str(item.get('staff_id', '')).strip()
                        if not user_id:
                            continue
                        row = [user_id, staff_id]
                        for col_name in col_names[2:]:
                            field_name = col_to_field.get(col_name, col_name)
                            value = item.get(field_name)
                            if isinstance(value, (list, dict)):
                                value = json.dumps(value, ensure_ascii=False)
                            row.append(str(value) if value is not None else None)
                        batch_data.append(tuple(row))
                    cursor.executemany(insert_sql, batch_data)
                    count += len(batch_data)
                self._adapter.commit(conn)
                on_clause = ' AND '.join([f'target.[{k}] = source.[{k}]' for k in ['id', 'staff_id']])
                update_set = ', '.join([f'target.[{c}] = source.[{c}]' for c in update_cols])
                source_vals = ', '.join([f'source.[{c}]' for c in col_names])
                merge_sql = f"MERGE INTO [{table_name}] WITH (HOLDLOCK) AS target USING (SELECT * FROM [{temp_table}]) AS source ON {on_clause} WHEN MATCHED THEN UPDATE SET {update_set} WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({source_vals})"
                cursor.execute(merge_sql)
                self._adapter.commit(conn)
                cursor.execute(f"DROP TABLE [{temp_table}]")
                self._adapter.commit(conn)
        return count
    
    def _save_batch(self, data_list: List[Dict], fields: Dict[str, str], batch_size: int = 500) -> int:
        if not data_list:
            return 0
        if not self._is_mysql:
            return self._update_batch(data_list, fields, batch_size)
        table_name = self.full_table_name
        count = 0
        q = self._q
        system_fields = {'created_at', 'updated_at'}
        col_names = [sanitize_column_name(f) for f in fields.keys() 
                    if sanitize_column_name(f).lower() not in system_fields]
        update_parts = [f'{q(col)} = VALUES({q(col)})' for col in col_names if col not in ('id', 'join_time')]
        update_clause = ', '.join(update_parts)
        placeholders = ', '.join([f'%({c})s' for c in col_names])
        sql = f"INSERT INTO {q(table_name)} ({', '.join([q(c) for c in col_names])}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"
        with self.db.get_connection() as conn:
            cursor = self._adapter.get_cursor(conn)
            for batch_start in range(0, len(data_list), batch_size):
                batch_end = min(batch_start + batch_size, len(data_list))
                batch = data_list[batch_start:batch_end]
                batch_data = []
                for item in batch:
                    row = {}
                    for field_name in fields.keys():
                        col_name = sanitize_column_name(field_name)
                        if col_name.lower() not in system_fields:
                            value = item.get(field_name)
                            if isinstance(value, (list, dict)):
                                value = json.dumps(value, ensure_ascii=False)
                            row[col_name] = value
                    batch_data.append(row)
                try:
                    cursor.executemany(sql, batch_data)
                    count += len(batch_data)
                except Exception as e:
                    self.logger.error(f"批量保存失败: {e}")
                self._adapter.commit(conn)
        return count
    
    def save_batch(self, data_list: List[Dict], batch_size: int = 500) -> int:
        """
        批量保存数据（兼容 BasePullService 接口）
        
        会自动调用 save_with_comparison 实现对比逻辑
        
        Args:
            data_list: 数据列表
            batch_size: 批量大小
            
        Returns:
            成功保存的数量
        """
        # 从 kwargs 中获取 debug 参数（如果 BasePullService 传递了的话）
        result = self.save_with_comparison(data_list, batch_size=batch_size, debug=False)
        return result['saved']
    
    def find_by_id(self, user_id: str, staff_id: str = None) -> Optional[Dict]:
        col_name = sanitize_column_name(self.UNIQUE_KEY)
        q, ph = self._q, self._ph
        params = [user_id]
        if self._is_mysql:
            sql = f"SELECT * FROM {q(self.full_table_name)} WHERE {q(col_name)} = {ph}"
            if staff_id:
                sql += f" AND {q('staff_id')} = {ph}"
                params.append(staff_id)
            sql += " LIMIT 1"
        else:
            sql = f"SELECT TOP 1 * FROM {q(self.full_table_name)} WHERE {q(col_name)} = {ph}"
            if staff_id:
                sql += f" AND {q('staff_id')} = {ph}"
                params.append(staff_id)
        return self.db.fetch_one(sql, tuple(params))
    
    def count(self, where: str = None, params: tuple = None) -> int:
        q = self._q
        sql = f"SELECT COUNT(*) as cnt FROM {q(self.full_table_name)}"
        if where:
            sql += f" WHERE {where}"
        result = self.db.fetch_one(sql, params)
        return result['cnt'] if result else 0
    
    def count_active(self) -> int:
        return self.count(where=f"{self._q('outflow_time')} IS NULL")
    
    def count_outflow(self) -> int:
        return self.count(where=f"{self._q('outflow_time')} IS NOT NULL")
    
    def get_outflow_by_date(self, outflow_date: str) -> List[Dict]:
        sql = f"SELECT * FROM {self._q(self.full_table_name)} WHERE {self._q('outflow_time')} = {self._ph}"
        return self.db.fetch_all(sql, (outflow_date,))
    
    def get_joined_by_date(self, join_date: str) -> List[Dict]:
        sql = f"SELECT * FROM {self._q(self.full_table_name)} WHERE {self._q('join_time')} = {self._ph}"
        return self.db.fetch_all(sql, (join_date,))

