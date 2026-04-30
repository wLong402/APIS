#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务队列模块 - 使用 Redis 实现消息队列和分布式锁

功能：
    - 失败任务入队
    - 分布式锁防止重复处理
    - 自动重试机制
    - 死信队列处理
"""

import json
import time
import uuid
from datetime import datetime
from typing import Dict, Optional, Callable
from dataclasses import dataclass, asdict

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("警告: redis 未安装，任务队列功能不可用。安装命令: pip install redis")


@dataclass
class RetryTask:
    """重试任务数据结构"""
    task_id: str                    # 任务ID
    api_type: str                   # API类型: trade/refund/erp/stockout
    start_time: str                 # 开始时间
    end_time: str                   # 结束时间
    expected_count: int             # 预期数量
    actual_count: int               # 实际数量
    shop_no: Optional[str] = None   # 店铺编号
    warehouse_no: Optional[str] = None  # 仓库编号
    retry_count: int = 0            # 已重试次数
    created_at: str = None          # 创建时间
    last_error: str = None          # 最后错误信息
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RetryTask':
        data = json.loads(json_str)
        return cls(**data)


class TaskQueue:
    """
    基于 Redis 的任务队列
    
    队列结构：
        - data_pull:retry_queue     : 重试队列（List）
        - data_pull:dead_queue      : 死信队列（List）
        - data_pull:processing      : 处理中的任务（Hash）
        - data_pull:lock:{task_key} : 分布式锁（String）
    """
    
    # 队列名称
    RETRY_QUEUE = "data_pull:retry_queue"
    DEAD_QUEUE = "data_pull:dead_queue"
    PROCESSING = "data_pull:processing"
    LOCK_PREFIX = "data_pull:lock:"
    
    # 配置
    MAX_RETRY = 3           # 最大重试次数
    LOCK_TIMEOUT = 300      # 锁超时时间（秒）
    RETRY_DELAY = 60        # 重试延迟（秒）
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 db: int = 0, password: str = None):
        """
        初始化任务队列
        
        Args:
            host: Redis 主机
            port: Redis 端口
            db: Redis 数据库编号
            password: Redis 密码
        """
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis 模块未安装")
        
        self.redis = redis.Redis(
            host=host, 
            port=port, 
            db=db, 
            password=password,
            decode_responses=True
        )
        self._check_connection()
    
    def _check_connection(self):
        """检查 Redis 连接"""
        try:
            self.redis.ping()
        except redis.ConnectionError as e:
            raise RuntimeError(f"无法连接 Redis: {e}")
    
    def _get_lock_key(self, task: RetryTask) -> str:
        """生成锁的 key"""
        return f"{self.LOCK_PREFIX}{task.api_type}:{task.start_time}:{task.end_time}"
    
    def acquire_lock(self, task: RetryTask, timeout: int = None) -> bool:
        """
        获取分布式锁
        
        Args:
            task: 任务对象
            timeout: 锁超时时间（秒）
            
        Returns:
            是否成功获取锁
        """
        lock_key = self._get_lock_key(task)
        timeout = timeout or self.LOCK_TIMEOUT
        
        # SET NX EX 原子操作
        return self.redis.set(lock_key, task.task_id, nx=True, ex=timeout)
    
    def release_lock(self, task: RetryTask) -> bool:
        """
        释放分布式锁
        
        Args:
            task: 任务对象
            
        Returns:
            是否成功释放锁
        """
        lock_key = self._get_lock_key(task)
        
        # Lua 脚本确保只释放自己的锁
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        return self.redis.eval(script, 1, lock_key, task.task_id) == 1
    
    def add_retry_task(self, api_type: str, start_time: str, end_time: str,
                       expected_count: int, actual_count: int,
                       shop_no: str = None, warehouse_no: str = None,
                       error: str = None) -> RetryTask:
        """
        添加重试任务到队列
        
        Args:
            api_type: API类型
            start_time: 开始时间
            end_time: 结束时间
            expected_count: 预期数量
            actual_count: 实际数量
            shop_no: 店铺编号
            warehouse_no: 仓库编号
            error: 错误信息
            
        Returns:
            创建的任务对象
        """
        task = RetryTask(
            task_id=str(uuid.uuid4()),
            api_type=api_type,
            start_time=start_time,
            end_time=end_time,
            expected_count=expected_count,
            actual_count=actual_count,
            shop_no=shop_no,
            warehouse_no=warehouse_no,
            last_error=error
        )
        
        # 加入重试队列
        self.redis.rpush(self.RETRY_QUEUE, task.to_json())
        
        return task
    
    def get_retry_task(self, timeout: int = 0) -> Optional[RetryTask]:
        """
        从队列获取一个重试任务
        
        Args:
            timeout: 阻塞等待时间（秒），0表示不阻塞
            
        Returns:
            任务对象，队列为空返回 None
        """
        if timeout > 0:
            result = self.redis.blpop(self.RETRY_QUEUE, timeout=timeout)
            if result:
                return RetryTask.from_json(result[1])
        else:
            result = self.redis.lpop(self.RETRY_QUEUE)
            if result:
                return RetryTask.from_json(result)
        return None
    
    def requeue_task(self, task: RetryTask, error: str = None):
        """
        重新入队（失败后重试）
        
        Args:
            task: 任务对象
            error: 错误信息
        """
        task.retry_count += 1
        task.last_error = error
        
        if task.retry_count >= self.MAX_RETRY:
            # 超过最大重试次数，进入死信队列
            self.redis.rpush(self.DEAD_QUEUE, task.to_json())
            print(f"[TaskQueue] 任务 {task.task_id} 超过最大重试次数，已移入死信队列")
        else:
            # 重新入队
            self.redis.rpush(self.RETRY_QUEUE, task.to_json())
            print(f"[TaskQueue] 任务 {task.task_id} 重新入队，已重试 {task.retry_count} 次")
    
    def mark_success(self, task: RetryTask):
        """标记任务成功"""
        self.release_lock(task)
        print(f"[TaskQueue] 任务 {task.task_id} 处理成功")
    
    def get_queue_stats(self) -> Dict:
        """获取队列统计信息"""
        return {
            'retry_queue_length': self.redis.llen(self.RETRY_QUEUE),
            'dead_queue_length': self.redis.llen(self.DEAD_QUEUE),
        }
    
    def get_dead_tasks(self, limit: int = 100) -> list:
        """获取死信队列中的任务"""
        tasks = self.redis.lrange(self.DEAD_QUEUE, 0, limit - 1)
        return [RetryTask.from_json(t) for t in tasks]
    
    def clear_dead_queue(self):
        """清空死信队列"""
        self.redis.delete(self.DEAD_QUEUE)


def create_task_queue_from_config(config_path: str = 'config/config.yaml') -> Optional[TaskQueue]:
    """
    从配置文件创建任务队列
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        TaskQueue 对象，如果 Redis 配置不存在则返回 None
    """
    if not REDIS_AVAILABLE:
        return None
    
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        redis_config = config.get('redis', {})
        if not redis_config:
            return None
        
        return TaskQueue(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0),
            password=redis_config.get('password')
        )
    except Exception as e:
        print(f"[TaskQueue] 初始化失败: {e}")
        return None


# 全局任务队列实例（懒加载）
_task_queue: Optional[TaskQueue] = None

def get_task_queue() -> Optional[TaskQueue]:
    """获取全局任务队列实例"""
    global _task_queue
    if _task_queue is None:
        _task_queue = create_task_queue_from_config()
    return _task_queue


def add_mismatch_task(api_type: str, start_time: str, end_time: str,
                      expected_count: int, actual_count: int,
                      shop_no: str = None, warehouse_no: str = None):
    """
    便捷方法：添加数据不匹配的重试任务
    
    Args:
        api_type: API类型
        start_time: 开始时间
        end_time: 结束时间
        expected_count: 预期数量
        actual_count: 实际数量
        shop_no: 店铺编号
        warehouse_no: 仓库编号
    """
    queue = get_task_queue()
    if queue:
        task = queue.add_retry_task(
            api_type=api_type,
            start_time=start_time,
            end_time=end_time,
            expected_count=expected_count,
            actual_count=actual_count,
            shop_no=shop_no,
            warehouse_no=warehouse_no,
            error=f"数据不匹配: 预期 {expected_count}, 实际 {actual_count}"
        )
        print(f"[TaskQueue] 已添加重试任务: {task.task_id}")
    else:
        print("[TaskQueue] Redis 未配置，跳过任务入队")





