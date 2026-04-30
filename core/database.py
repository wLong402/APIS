# -*- coding: utf-8 -*-
"""
数据库管理模块

提供数据库连接池和基础操作
"""

import json
import re
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Generator
from queue import Queue, Empty
from threading import Lock
import time

from .config import Config, get_config
from .logger import get_logger
from .exceptions import DatabaseError
from .db_adapter import get_adapter, DatabaseAdapter

logger = get_logger('core.database')


class ConnectionPool:
    """
    简单的数据库连接池
    
    特性:
        - 连接复用，避免频繁创建/销毁
        - 自动重连机制
        - 连接有效性检查
        - 线程安全
    """
    
    def __init__(self, 
                 db_type: str,
                 host: str,
                 port: int,
                 user: str,
                 password: str,
                 database: str,
                 charset: str = 'utf8mb4',
                 driver: str = None,
                 pool_size: int = 10,
                 max_overflow: int = 5,
                 pool_timeout: int = 30,
                 recycle_time: int = 3600):
        """
        初始化连接池
        
        Args:
            host: 数据库主机
            port: 端口
            user: 用户名
            password: 密码
            database: 数据库名
            charset: 字符集
            pool_size: 核心连接数
            max_overflow: 最大溢出连接数（总连接 = pool_size + max_overflow）
            pool_timeout: 获取连接超时时间（秒）
            recycle_time: 连接回收时间（秒），超过此时间的连接会被关闭重建
        """
        self.db_type = db_type
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self.driver = driver
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.recycle_time = recycle_time
        
        self.adapter = get_adapter(db_type)
        
        self._pool = Queue(maxsize=pool_size)
        self._overflow_count = 0
        self._lock = Lock()
        self._connection_times = {}  # 记录连接创建时间
        
        # 预创建连接
        self._init_pool()
    
    def _init_pool(self):
        """初始化连接池"""
        for _ in range(self.pool_size):
            try:
                conn = self._create_connection()
                self._pool.put(conn)
            except Exception as e:
                logger.warning(f"初始化连接池失败: {e}")
    
    def _create_connection(self):
        """创建新连接"""
        conn = self.adapter.create_connection(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset=self.charset,
            driver=self.driver
        )
        # 记录创建时间
        self._connection_times[id(conn)] = time.time()
        return conn
    
    def _is_connection_valid(self, conn) -> bool:
        """检查连接是否有效"""
        try:
            # 检查连接是否超时需要回收
            create_time = self._connection_times.get(id(conn), 0)
            if time.time() - create_time > self.recycle_time:
                return False
            
            # 执行简单查询测试连接
            return self.adapter.ping_connection(conn)
        except Exception:
            return False
    
    def get_connection(self):
        """
        获取数据库连接
        
        Returns:
            pymysql.Connection
            
        Raises:
            DatabaseError: 无法获取连接
        """
        # 1. 尝试从池中获取
        try:
            conn = self._pool.get(timeout=0.1)
            if self._is_connection_valid(conn):
                return conn
            else:
                # 连接无效，关闭后创建新的
                self._close_connection(conn)
                return self._create_connection()
        except Empty:
            pass
        
        # 2. 池为空，尝试创建溢出连接
        with self._lock:
            if self._overflow_count < self.max_overflow:
                self._overflow_count += 1
                try:
                    return self._create_connection()
                except Exception as e:
                    self._overflow_count -= 1
                    raise DatabaseError(f"创建数据库连接失败: {e}")
        
        # 3. 等待池中有可用连接
        try:
            conn = self._pool.get(timeout=self.pool_timeout)
            if self._is_connection_valid(conn):
                return conn
            else:
                self._close_connection(conn)
                return self._create_connection()
        except Empty:
            raise DatabaseError(f"获取数据库连接超时（{self.pool_timeout}秒）")
    
    def return_connection(self, conn, is_overflow: bool = False):
        """
        归还连接到池
        
        Args:
            conn: 数据库连接
            is_overflow: 是否是溢出连接
        """
        if is_overflow:
            with self._lock:
                self._overflow_count -= 1
            self._close_connection(conn)
        else:
            try:
                # 回滚未提交的事务
                self.adapter.rollback(conn)
                self._pool.put_nowait(conn)
            except Exception:
                self._close_connection(conn)
    
    def _close_connection(self, conn):
        """关闭连接"""
        try:
            self._connection_times.pop(id(conn), None)
            self.adapter.close_connection(conn)
        except Exception:
            pass
    
    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                self._close_connection(conn)
            except Empty:
                break
    
    @property
    def size(self) -> int:
        """当前池中连接数"""
        return self._pool.qsize()
    
    @property
    def overflow(self) -> int:
        """当前溢出连接数"""
        return self._overflow_count


class DatabaseManager:
    """
    数据库连接管理器
    
    提供连接池管理和基础操作
    """
    
    def __init__(self, config: Config = None):
        """
        初始化数据库管理器
        
        Args:
            config: 配置对象，为空时自动加载
        """
        self.config = config or get_config()
        self.db_config = self.config.database
        
        # 创建连接池
        self._pool = ConnectionPool(
            db_type=self.db_config.type,
            host=self.db_config.host,
            port=self.db_config.port,
            user=self.db_config.user,
            password=self.db_config.password,
            database=self.db_config.database,
            charset=self.db_config.charset,
            driver=getattr(self.db_config, 'driver', None),
            pool_size=self.db_config.pool_size,
        )
        
        self.adapter = self._pool.adapter
        
        logger.info(f"数据库连接池已初始化 (size={self.db_config.pool_size})")
    
    @contextmanager
    def get_connection(self) -> Generator:
        """
        获取数据库连接（上下文管理器）
        
        使用方式:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
        
        Yields:
            pymysql.Connection
        """
        conn = None
        is_overflow = False
        
        try:
            # 检查是否会是溢出连接
            is_overflow = self._pool.size == 0 and self._pool.overflow < self._pool.max_overflow
            conn = self._pool.get_connection()
            yield conn
        except Exception as e:
            logger.error(f"数据库操作失败: {e}")
            raise DatabaseError(f"数据库操作失败: {e}")
        finally:
            if conn:
                self._pool.return_connection(conn, is_overflow)
    
    def execute(self, sql: str, params: tuple = None) -> int:
        """
        执行 SQL 语句
        
        Args:
            sql: SQL 语句
            params: 参数
            
        Returns:
            影响的行数
        """
        with self.get_connection() as conn:
            cursor = self.adapter.get_cursor(conn)
            if params is not None:
                affected = cursor.execute(sql, params)
            else:
                affected = cursor.execute(sql)
            self.adapter.commit(conn)
            return affected
    
    def fetch_one(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """查询单条记录"""
        with self.get_connection() as conn:
            cursor = self.adapter.get_cursor(conn)
            if params is not None:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            row = cursor.fetchone()
            # SQL Server pyodbc 返回 Row 对象，需要转换为字典
            if row and not isinstance(row, dict):
                columns = [column[0] for column in cursor.description]
                return dict(zip(columns, row))
            return row
    
    def fetch_all(self, sql: str, params: tuple = None) -> List[Dict]:
        """查询多条记录"""
        with self.get_connection() as conn:
            cursor = self.adapter.get_cursor(conn)
            if params is not None:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            rows = cursor.fetchall()
            # SQL Server pyodbc 返回 Row 对象，需要转换为字典
            if rows and rows[0] and not isinstance(rows[0], dict):
                columns = [column[0] for column in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            return rows
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        sql, params = self.adapter.table_exists_sql(self.db_config.database, table_name)
        result = self.fetch_one(sql, params)
        return result['cnt'] > 0 if result else False
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """获取表的所有列名"""
        sql, params = self.adapter.get_columns_sql(table_name)
        result = self.fetch_all(sql, params)
        return self.adapter.parse_columns(result)
    
    def close(self):
        """关闭连接池"""
        self._pool.close_all()
        logger.info("数据库连接池已关闭")
    
    @property
    def pool_status(self) -> Dict[str, int]:
        """获取连接池状态"""
        return {
            'pool_size': self._pool.size,
            'overflow': self._pool.overflow,
            'max_overflow': self._pool.max_overflow
        }


# ============ 工具函数 ============

def sanitize_column_name(name: str) -> str:
    """
    清理列名，确保符合 MySQL 规范
    
    Args:
        name: 原始列名
        
    Returns:
        清理后的列名
    """
    # 替换特殊字符
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # 如果以数字开头，添加前缀
    if name and name[0].isdigit():
        name = 'col_' + name
    # MySQL 保留字处理
    reserved_words = {
        'order', 'group', 'select', 'from', 'where', 
        'index', 'key', 'status', 'type', 'desc', 'asc',
        'limit', 'offset', 'having', 'join', 'on', 'and', 'or'
    }
    if name.lower() in reserved_words:
        name = name + '_'
    return name


def infer_column_type(value: Any, db_type: str = 'mysql') -> str:
    """
    根据 Python 值推断数据库列类型
    
    Args:
        value: Python 值
        db_type: 数据库类型
        
    Returns:
        数据库类型字符串
    """
    from .db_adapter import get_adapter
    adapter = get_adapter(db_type)
    return adapter.infer_column_type(value)


infer_mysql_type = infer_column_type


# ============ 全局实例 ============

_db_manager: Optional[DatabaseManager] = None


def get_db_manager(config: Config = None) -> DatabaseManager:
    """
    获取全局数据库管理器实例
    
    Args:
        config: 配置对象（首次调用时可传入）
        
    Returns:
        DatabaseManager 实例
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(config)
    return _db_manager


def reset_db_manager(config: Config = None) -> DatabaseManager:
    """重置全局数据库管理器实例"""
    global _db_manager
    if _db_manager is not None:
        try:
            _db_manager.close()
        except Exception:
            pass
    _db_manager = DatabaseManager(config) if config is not None else None
    return get_db_manager(config)
