# -*- coding: utf-8 -*-
"""
客户详情-员工关系数据仓库

存储从 batch_get 接口获取的 follow_staffs 数据
唯一键：id + staff_id
"""

import json
from datetime import date
from typing import List, Dict, Set, Optional

from core.database import (
    DatabaseManager, get_db_manager,
    sanitize_column_name, infer_mysql_type
)
from core.logger import get_logger


class FollowStaffRepository:
    """
    客户-员工关系数据仓库
    
    存储客户详情中的 follow_staffs 数据，每条记录对应一个客户与一个员工的关系。
    唯一键：(id, staff_id)
    """
    
    TABLE_NAME = 'follow_staff'
    SYSTEM_PREFIX = 'weiban'
    COMPOSITE_UNIQUE_KEY = ('id', 'staff_id')
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or get_db_manager()
        self.logger = get_logger(f'{self.SYSTEM_PREFIX}.{self.TABLE_NAME}')
    
    @property
    def full_table_name(self) -> str:
        return f'{self.SYSTEM_PREFIX}_{self.TABLE_NAME}'
    
    def _make_composite_key(self, item: Dict) -> str:
        """生成复合唯一键"""
        user_id = str(item.get('id', '')).strip()
        staff_id = str(item.get('staff_id', '')).strip()
        if not user_id or not staff_id:
            return ''
        return f"{user_id}_{staff_id}"
    
    def save_batch(self, data_list: List[Dict], batch_size: int = 500,
                   debug: bool = False, progress_label: str = '', **kwargs) -> int:
        """
        批量保存数据
        
        Args:
            data_list: 数据列表，每条数据需包含 id 和 staff_id
            batch_size: 批次大小
            debug: 是否打印调试信息
            
        Returns:
            保存的记录数
        """
        from core.logger import debug_print
        
        if not data_list:
            return 0
        
        if debug:
            debug_print(f"    开始保存 {len(data_list)} 条客户-员工关系数据...")
        
        # 分析字段
        fields = self._analyze_fields(data_list)
        # 强制 id 和 staff_id 使用 VARCHAR(255)
        fields['id'] = 'VARCHAR(255)'
        fields['staff_id'] = 'VARCHAR(255)'
        fields['pull_date'] = 'DATE'
        
        # 确保表结构
        self._ensure_table(fields)
        self._ensure_columns(fields)
        
        today_str = date.today().strftime('%Y-%m-%d')
        
        # 使用 INSERT ... ON DUPLICATE KEY UPDATE
        table_name = self.full_table_name
        count = 0
        
        system_fields = {'created_at', 'updated_at'}
        col_names = [sanitize_column_name(f) for f in fields.keys() 
                    if sanitize_column_name(f).lower() not in system_fields]
        
        # 确保 id 和 staff_id 在最前面
        if 'id' in col_names:
            col_names.remove('id')
        if 'staff_id' in col_names:
            col_names.remove('staff_id')
        col_names.insert(0, 'id')
        col_names.insert(1, 'staff_id')
        
        update_cols = [col for col in col_names if col not in ('id', 'staff_id')]
        update_parts = ', '.join([f'`{col}` = VALUES(`{col}`)' for col in update_cols])
        placeholders = ', '.join([f'%({col})s' for col in col_names])
        
        sql = f"""
            INSERT INTO `{table_name}` ({', '.join([f'`{c}`' for c in col_names])})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_parts}
        """
        
        total = len(data_list)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            for batch_idx, batch_start in enumerate(range(0, total, batch_size), 1):
                batch_end = min(batch_start + batch_size, total)
                batch = data_list[batch_start:batch_end]
                
                batch_data = []
                for item in batch:
                    user_id = str(item.get('id', '')).strip()
                    staff_id = str(item.get('staff_id', '')).strip()
                    if not user_id or not staff_id:
                        continue
                    
                    row = {'id': user_id, 'staff_id': staff_id, 'pull_date': today_str}
                    
                    for field_name in fields.keys():
                        col_name = sanitize_column_name(field_name)
                        if col_name.lower() not in system_fields and col_name not in ('id', 'staff_id', 'pull_date'):
                            value = item.get(field_name)
                            if isinstance(value, (list, dict)):
                                value = json.dumps(value, ensure_ascii=False)
                            row[col_name] = value
                    
                    batch_data.append(row)
                
                try:
                    cursor.executemany(sql, batch_data)
                    count += len(batch_data)
                    conn.commit()
                    
                    if debug and batch_idx % 10 == 0:
                        debug_print(f"    进度: {count}/{total} 条")
                except Exception as e:
                    self.logger.error(f"批量保存失败: {e}")
                    conn.rollback()
        
        if debug:
            debug_print(f"    保存完成: {count} 条")
        
        return count
    
    def _analyze_fields(self, data_list: List[Dict], sample_size: int = 100) -> Dict[str, str]:
        """分析数据字段和类型"""
        fields = {}
        
        for item in data_list[:sample_size]:
            for key, value in item.items():
                if key not in fields:
                    fields[key] = infer_mysql_type(value)
                elif value is not None and fields[key] == 'TEXT':
                    new_type = infer_mysql_type(value)
                    if new_type != 'TEXT':
                        fields[key] = new_type
        
        return fields
    
    def _ensure_table(self, fields: Dict[str, str]):
        """确保表存在"""
        table_name = self.full_table_name
        
        columns = ['pk_id INT AUTO_INCREMENT PRIMARY KEY']
        for field_name, field_type in fields.items():
            col_name = sanitize_column_name(field_name)
            if col_name.lower() not in ('created_at', 'updated_at'):
                columns.append(f'`{col_name}` {field_type}')
        
        columns.append('created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        columns.append('updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')
        
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS `{table_name}` (
                {', '.join(columns)}
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
        """
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_sql)
            
            # 检查复合唯一索引是否存在
            index_name = 'idx_user_staff'
            cursor.execute(f"""
                SELECT COUNT(*) as cnt FROM information_schema.statistics 
                WHERE table_schema = DATABASE() 
                AND table_name = '{table_name}' 
                AND index_name = '{index_name}'
            """)
            result = cursor.fetchone()
            
            if not (result and result['cnt'] > 0):
                try:
                    # 先确保列类型
                    try:
                        cursor.execute(f"ALTER TABLE `{table_name}` MODIFY COLUMN `id` VARCHAR(255)")
                        cursor.execute(f"ALTER TABLE `{table_name}` MODIFY COLUMN `staff_id` VARCHAR(255)")
                        conn.commit()
                    except:
                        pass
                    
                    # 删除重复数据
                    cursor.execute(f"""
                        DELETE t1 FROM `{table_name}` t1
                        INNER JOIN `{table_name}` t2 
                        WHERE t1.`id` = t2.`id` 
                        AND t1.`staff_id` = t2.`staff_id` 
                        AND t1.`pk_id` < t2.`pk_id`
                    """)
                    conn.commit()
                    
                    # 创建唯一索引
                    cursor.execute(f"""
                        ALTER TABLE `{table_name}` 
                        ADD UNIQUE INDEX `{index_name}` (`id`, `staff_id`)
                    """)
                    conn.commit()
                    self.logger.info(f"已为表 {table_name} 添加复合唯一索引 (id, staff_id)")
                except Exception as e:
                    self.logger.warning(f"添加复合唯一索引失败: {e}")
            
            conn.commit()
    
    def _ensure_columns(self, fields: Dict[str, str]):
        """确保所有列存在"""
        table_name = self.full_table_name
        
        existing = set(self.db.get_table_columns(table_name))
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            for field_name, field_type in fields.items():
                col_name = sanitize_column_name(field_name)
                if col_name.lower() not in existing and col_name.lower() not in ('created_at', 'updated_at'):
                    try:
                        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {field_type}")
                    except:
                        pass
            
            conn.commit()
    
    def get_all_user_ids(self) -> Set[str]:
        """获取表中所有的客户ID"""
        table_name = self.full_table_name
        
        # 检查表是否存在
        check_sql = f"""
            SELECT COUNT(*) as cnt FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = '{table_name}'
        """
        result = self.db.fetch_one(check_sql)
        
        if not result or result['cnt'] == 0:
            return set()
        
        sql = f"SELECT DISTINCT `id` FROM `{table_name}`"
        rows = self.db.fetch_all(sql)
        return {str(row['id']).strip() for row in rows if row.get('id')}
    
    def count(self) -> int:
        """统计记录数"""
        table_name = self.full_table_name
        sql = f"SELECT COUNT(*) as cnt FROM `{table_name}`"
        try:
            result = self.db.fetch_one(sql)
            return result['cnt'] if result else 0
        except:
            return 0

