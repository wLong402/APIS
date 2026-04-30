# -*- coding: utf-8 -*-
"""
数据库适配器

提供多数据库支持的抽象层
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import json


class DatabaseAdapter(ABC):
    """数据库适配器基类"""
    
    @abstractmethod
    def create_connection(self, **kwargs):
        """创建数据库连接"""
        pass
    
    @abstractmethod
    def ping_connection(self, conn) -> bool:
        """检查连接是否有效"""
        pass
    
    @abstractmethod
    def close_connection(self, conn):
        """关闭连接"""
        pass
    
    @abstractmethod
    def get_cursor(self, conn):
        """获取游标"""
        pass
    
    @abstractmethod
    def commit(self, conn):
        """提交事务"""
        pass
    
    @abstractmethod
    def rollback(self, conn):
        """回滚事务"""
        pass
    
    @abstractmethod
    def table_exists_sql(self, database: str, table_name: str) -> tuple:
        """生成检查表是否存在的SQL"""
        pass
    
    @abstractmethod
    def get_columns_sql(self, table_name: str) -> tuple:
        """生成获取表列的SQL，返回(sql, params)"""
        pass
    
    @abstractmethod
    def parse_columns(self, result: List[Dict]) -> List[str]:
        """解析列名查询结果"""
        pass
    
    @abstractmethod
    def upsert_sql(self, table_name: str, columns: List[str], unique_key: str = None) -> str:
        """生成UPSERT语句"""
        pass
    
    @abstractmethod
    def infer_column_type(self, value: Any) -> str:
        """推断列类型"""
        pass
    
    @abstractmethod
    def build_create_table_sql(self, table_name: str, columns: List[tuple], unique_key: str = None) -> str:
        """构建创建表SQL"""
        pass

    def quote(self, name: str) -> str:
        """引用标识符"""
        pass


class MySQLAdapter(DatabaseAdapter):
    """MySQL 适配器"""
    
    def create_connection(self, **kwargs):
        import pymysql
        from pymysql.cursors import DictCursor
        return pymysql.connect(
            host=kwargs['host'],
            port=kwargs['port'],
            user=kwargs['user'],
            password=kwargs['password'],
            database=kwargs['database'],
            charset=kwargs.get('charset', 'utf8mb4'),
            cursorclass=DictCursor,
            autocommit=False
        )
    
    def ping_connection(self, conn) -> bool:
        try:
            conn.ping(reconnect=False)
            return True
        except:
            return False
    
    def close_connection(self, conn):
        try:
            conn.close()
        except:
            pass
    
    def get_cursor(self, conn):
        return conn.cursor()
    
    def commit(self, conn):
        conn.commit()
    
    def rollback(self, conn):
        conn.rollback()
    
    def table_exists_sql(self, database: str, table_name: str) -> tuple:
        sql = """
            SELECT COUNT(*) as cnt 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s
        """
        return (sql, (database, table_name))
    
    def get_columns_sql(self, table_name: str) -> tuple:
        return (f"DESCRIBE `{table_name}`", None)
    
    def parse_columns(self, result: List[Dict]) -> List[str]:
        return [row['Field'].lower() for row in result]
    
    def upsert_sql(self, table_name: str, columns: List[str], unique_key = None) -> str:
        col_list = ', '.join([f'`{c}`' for c in columns])
        placeholders = ', '.join([f'%({c})s' for c in columns])
        
        if unique_key:
            keys = unique_key if isinstance(unique_key, (list, tuple)) else [unique_key]
            update_parts = [f'`{col}` = VALUES(`{col}`)' for col in columns if col not in keys]
            update_clause = ', '.join(update_parts)
            return f"""
                INSERT INTO `{table_name}` ({col_list})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {update_clause}
            """
        else:
            return f"""
                INSERT INTO `{table_name}` ({col_list})
                VALUES ({placeholders})
            """
    
    def infer_column_type(self, value: Any) -> str:
        if value is None:
            return 'TEXT'
        if isinstance(value, bool):
            return 'TINYINT(1)'
        if isinstance(value, int):
            return 'BIGINT'
        if isinstance(value, float):
            return 'DECIMAL(19,4)'
        if isinstance(value, (list, dict)):
            return 'LONGTEXT'
        if isinstance(value, str):
            return 'TEXT'
        return 'TEXT'
    
    def build_create_table_sql(self, table_name: str, columns: List[tuple], unique_key = None) -> str:
        col_defs = []
        for col_name, col_type in columns:
            col_defs.append(f'`{col_name}` {col_type}')
        
        if unique_key:
            keys = unique_key if isinstance(unique_key, (list, tuple)) else [unique_key]
            uk_name = '_'.join(keys)
            uk_cols = ', '.join([f'`{k}`' for k in keys])
            col_defs.append(f'UNIQUE KEY `uk_{uk_name}` ({uk_cols})')
        
        col_defs.append('`created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        col_defs.append('`updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')
        
        return f"""
            CREATE TABLE IF NOT EXISTS `{table_name}` (
                {', '.join(col_defs)}
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """

    def quote(self, name: str) -> str:
        return f'`{name}`'


class SQLServerAdapter(DatabaseAdapter):
    """SQL Server 适配器"""
    
    def create_connection(self, **kwargs):
        import pyodbc
        driver = kwargs.get('driver', 'ODBC Driver 17 for SQL Server')
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={kwargs['host']},{kwargs['port']};"
            f"DATABASE={kwargs['database']};"
            f"UID={kwargs['user']};"
            f"PWD={kwargs['password']}"
        )
        return pyodbc.connect(conn_str, autocommit=False)
    
    def ping_connection(self, conn) -> bool:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except:
            return False
    
    def close_connection(self, conn):
        try:
            conn.close()
        except:
            pass
    
    def get_cursor(self, conn):
        cursor = conn.cursor()
        cursor.fast_executemany = True
        return cursor
    
    def commit(self, conn):
        conn.commit()
    
    def rollback(self, conn):
        conn.rollback()
    
    def table_exists_sql(self, database: str, table_name: str) -> tuple:
        sql = """
            SELECT COUNT(*) as cnt 
            FROM information_schema.tables 
            WHERE table_catalog = ? AND table_name = ?
        """
        return (sql, (database, table_name))
    
    def get_columns_sql(self, table_name: str) -> tuple:
        sql = """
            SELECT COLUMN_NAME as Field
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
        """
        return (sql, (table_name,))
    
    def parse_columns(self, result: List[Dict]) -> List[str]:
        return [row['Field'].lower() for row in result]
    
    def upsert_sql(self, table_name: str, columns: List[str], unique_key = None) -> str:
        col_list = ', '.join([f'[{c}]' for c in columns])
        placeholders = ', '.join(['?' for _ in columns])
        
        if unique_key:
            keys = unique_key if isinstance(unique_key, (list, tuple)) else [unique_key]
            source_cols = ', '.join([f'[{c}]' for c in columns])
            source_vals = ', '.join([f'source.[{c}]' for c in columns])
            on_clause = ' AND '.join([f'target.[{k}] = source.[{k}]' for k in keys])
            update_set = ', '.join([f'target.[{col}] = source.[{col}]' for col in columns if col not in keys])
            
            return f"""
                MERGE INTO [{table_name}] AS target
                USING (VALUES ({placeholders})) AS source ({source_cols})
                ON {on_clause}
                WHEN MATCHED THEN
                    UPDATE SET {update_set}
                WHEN NOT MATCHED THEN
                    INSERT ({col_list})
                    VALUES ({source_vals});
            """
        else:
            return f"""
                INSERT INTO [{table_name}] ({col_list})
                VALUES ({placeholders})
            """
    
    def infer_column_type(self, value: Any) -> str:
        if value is None:
            return 'NVARCHAR(MAX)'
        if isinstance(value, bool):
            return 'BIT'
        if isinstance(value, int):
            return 'BIGINT'
        if isinstance(value, float):
            return 'DECIMAL(19,4)'
        if isinstance(value, (list, dict)):
            return 'NVARCHAR(MAX)'
        if isinstance(value, str):
            return 'NVARCHAR(MAX)'
        return 'NVARCHAR(MAX)'
    
    def build_create_table_sql(self, table_name: str, columns: List[tuple], unique_key = None) -> str:
        col_defs = []
        col_defs.append('[id] BIGINT IDENTITY(1,1) PRIMARY KEY')
        
        for col_name, col_type in columns:
            col_defs.append(f'[{col_name}] {col_type}')
        
        col_defs.append('[created_at] DATETIME DEFAULT GETDATE()')
        col_defs.append('[updated_at] DATETIME DEFAULT GETDATE()')
        
        create_table_sql = f"""
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[{table_name}]') AND type in (N'U'))
CREATE TABLE [{table_name}] (
    {', '.join(col_defs)}
)
"""
        
        return create_table_sql
    
    def build_unique_constraint_sql(self, table_name: str, unique_key) -> str:
        keys = unique_key if isinstance(unique_key, (list, tuple)) else [unique_key]
        uk_name = '_'.join(keys)
        uk_cols = ', '.join([f'[{k}]' for k in keys])
        return f"""
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[{table_name}]') AND name = N'UK_{uk_name}')
BEGIN
    BEGIN TRY
        ALTER TABLE [{table_name}] ADD CONSTRAINT [UK_{uk_name}] UNIQUE ({uk_cols})
    END TRY
    BEGIN CATCH
    END CATCH
END
"""

    def quote(self, name: str) -> str:
        return f'[{name}]'


def get_adapter(db_type: str) -> DatabaseAdapter:
    """获取数据库适配器"""
    adapters = {
        'mysql': MySQLAdapter,
        'sqlserver': SQLServerAdapter,
    }
    
    adapter_class = adapters.get(db_type.lower())
    if not adapter_class:
        raise ValueError(f"不支持的数据库类型: {db_type}")
    
    return adapter_class()
