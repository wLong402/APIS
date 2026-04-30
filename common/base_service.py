# -*- coding: utf-8 -*-
"""
数据拉取服务基类

所有数据拉取服务都应继承此基类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import time

from core.logger import get_logger, debug_print


@dataclass
class PullResult:
    """拉取结果"""
    fetched: int = 0          # 获取的数据量
    saved: int = 0            # 保存成功的数据量
    errors: int = 0           # 错误数量
    duration: float = 0       # 耗时（秒）
    details: Dict = field(default_factory=dict)  # 详细信息
    
    @property
    def success(self) -> bool:
        """是否完全成功（无错误且数量匹配）"""
        return self.errors == 0 and self.fetched == self.saved
    
    def to_dict(self) -> Dict:
        return {
            'fetched': self.fetched,
            'saved': self.saved,
            'errors': self.errors,
            'duration': round(self.duration, 2),
            'success': self.success,
            'details': self.details,
        }
    
    def __add__(self, other: 'PullResult') -> 'PullResult':
        """支持结果合并"""
        return PullResult(
            fetched=self.fetched + other.fetched,
            saved=self.saved + other.saved,
            errors=self.errors + other.errors,
            duration=self.duration + other.duration,
            details={**self.details, **other.details}
        )


class BasePullService(ABC):
    """
    数据拉取服务基类
    
    使用模板方法模式，子类只需实现:
        - _fetch_data(): 从 API 获取数据
        
    可选覆盖:
        - _get_api_name(): 返回 API 名称（用于日志）
        - before_pull(): 拉取前钩子
        - after_pull(): 拉取后钩子
        - on_error(): 错误处理钩子
    
    子类必须定义:
        - SERVICE_NAME: 服务名称（如 'trade', 'refund'）
        - SYSTEM_NAME: 所属系统（如 'wdt', 'jdy'）
    """
    
    # 服务标识（子类必须定义）
    SERVICE_NAME: str = None
    SYSTEM_NAME: str = None
    
    # API 名称（用于日志记录，子类可覆盖）
    API_NAME: str = None
    
    def __init__(self, client=None, repository=None):
        """
        初始化服务
        
        Args:
            client: API 客户端
            repository: 数据仓库
        """
        if self.SERVICE_NAME is None or self.SYSTEM_NAME is None:
            raise NotImplementedError("子类必须定义 SERVICE_NAME 和 SYSTEM_NAME")
        
        self.client = client
        self.repo = repository
        self.logger = get_logger(f"service.{self.SYSTEM_NAME}.{self.SERVICE_NAME}")
    
    # ============ 模板方法（子类必须实现） ============
    
    @abstractmethod
    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        """
        从 API 获取数据（子类必须实现）
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            **kwargs: 其他参数（debug, page_size, max_workers 等）
            
        Returns:
            数据列表
        """
        pass
    
    # ============ 可选钩子方法（子类可覆盖） ============
    
    def _get_api_name(self) -> str:
        """获取 API 名称（用于日志记录）"""
        return self.API_NAME or f"{self.SYSTEM_NAME}_{self.SERVICE_NAME}"
    
    def before_pull(self, start_time: str, end_time: str, **kwargs) -> None:
        """
        拉取前钩子
        
        可用于：参数验证、日志记录、资源准备等
        """
        pass
    
    def after_pull(self, result: PullResult, start_time: str, end_time: str, **kwargs) -> None:
        """
        拉取后钩子
        
        可用于：结果处理、通知、清理等
        """
        pass
    
    def on_error(self, error: Exception, start_time: str, end_time: str, **kwargs) -> None:
        """
        错误处理钩子
        
        可用于：错误记录、告警、重试入队等
        """
        self.logger.error(f"拉取失败 [{start_time} ~ {end_time}]: {error}")
    
    def _on_data_mismatch(self, result: PullResult, start_time: str, end_time: str) -> None:
        """
        数据不匹配处理
        
        可用于：记录异常、入队重试等
        """
        from core.logger import log_data_mismatch
        log_data_mismatch(
            api_name=self._get_api_name(),
            time_range=f"{start_time} ~ {end_time}",
            expected=result.fetched,
            actual=result.saved,
            connector=self.SYSTEM_NAME
        )
    
    # ============ 核心方法（模板方法模式） ============
    
    def pull(self, start_time: str, end_time: str, **kwargs) -> PullResult:
        """
        拉取数据（模板方法）
        
        执行流程:
            1. before_pull() - 前置钩子
            2. _fetch_data() - 获取数据
            3. repo.save_batch() - 保存数据
            4. after_pull() - 后置钩子
        
        Args:
            start_time: 开始时间，格式 'YYYY-MM-DD HH:MM:SS'
            end_time: 结束时间，格式 'YYYY-MM-DD HH:MM:SS'
            **kwargs: 其他参数
            
        Returns:
            PullResult 拉取结果
        """
        start_ts = time.time()
        result = PullResult()
        
        try:
            # 1. 前置钩子
            self.before_pull(start_time, end_time, **kwargs)
            
            # 2. 获取数据
            data = self._fetch_data(start_time, end_time, **kwargs)
            result.fetched = len(data) if data else 0
            
            # 3. 保存数据
            if data and self.repo:
                result.saved = self.repo.save_batch(data)
            elif data:
                result.saved = result.fetched  # 无仓库时视为全部成功
            
            # 4. 计算错误数
            result.errors = result.fetched - result.saved
            
            # 5. 数据不匹配处理
            if result.errors > 0:
                self._on_data_mismatch(result, start_time, end_time)
            
            # 6. 后置钩子
            self.after_pull(result, start_time, end_time, **kwargs)
            
        except Exception as e:
            self.on_error(e, start_time, end_time, **kwargs)
            result.errors = 1
            result.details['error'] = str(e)
        
        result.duration = time.time() - start_ts
        return result
    
    def pull_by_interval(self, start_time: str, end_time: str, 
                         interval_seconds: int, 
                         debug: bool = False,
                         **kwargs) -> PullResult:
        """
        按时间间隔拉取数据
        
        将大的时间范围切分为小间隔，逐个拉取。
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            interval_seconds: 间隔秒数（如 3600 表示 1 小时）
            debug: 是否打印调试信息
            **kwargs: 传递给 pull() 的其他参数
            
        Returns:
            PullResult 汇总结果
        """
        start_ts = time.time()
        
        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        
        # 计算总间隔数
        total_seconds = (end_dt - start_dt).total_seconds()
        total_intervals = int(total_seconds / interval_seconds) + (1 if total_seconds % interval_seconds else 0)
        
        # 格式化间隔显示
        if interval_seconds >= 3600:
            interval_text = f"{interval_seconds // 3600}小时"
        elif interval_seconds >= 60:
            interval_text = f"{interval_seconds // 60}分钟"
        else:
            interval_text = f"{interval_seconds}秒"
        
        # 总是显示基本进度
        print(f"[{self.SYSTEM_NAME}.{self.SERVICE_NAME}] 按{interval_text}拉取，共 {total_intervals} 个时段", flush=True)
        
        # 汇总结果
        total_result = PullResult()
        errors_list = []
        
        current = start_dt
        interval_count = 0
        
        while current < end_dt:
            interval_count += 1
            interval_start = current.strftime("%Y-%m-%d %H:%M:%S")
            
            # 计算间隔结束时间
            interval_end_dt = min(current + timedelta(seconds=interval_seconds), end_dt)
            interval_end = (interval_end_dt - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
            
            # 总是显示进度
            print(f"\n  [{interval_count}/{total_intervals}] {interval_start} ~ {interval_end}", flush=True)
            
            try:
                result = self.pull(interval_start, interval_end, debug=debug, **kwargs)
                total_result.fetched += result.fetched
                total_result.saved += result.saved
                total_result.errors += result.errors
                
                if result.fetched > 0:
                    print(f"    获取 {result.fetched} 条，保存 {result.saved} 条", flush=True)
                else:
                    print(f"    无数据", flush=True)
                    
            except Exception as e:
                self.logger.error(f"拉取失败 [{interval_start} ~ {interval_end}]: {e}")
                errors_list.append({
                    'interval': f"{interval_start} ~ {interval_end}",
                    'error': str(e)
                })
                total_result.errors += 1
            
            current = interval_end_dt
        
        total_result.duration = time.time() - start_ts
        total_result.details = {
            'intervals': interval_count,
            'interval_seconds': interval_seconds,
            'errors_list': errors_list if errors_list else None,
        }
        
        print(f"\n[{self.SYSTEM_NAME}.{self.SERVICE_NAME}] 完成，共获取 {total_result.fetched} 条，保存 {total_result.saved} 条，耗时 {total_result.duration:.2f}s")
        
        return total_result
    
    def pull_by_day(self, start_date: str, end_date: str, 
                    interval_seconds: int = 0,
                    debug: bool = False,
                    **kwargs) -> PullResult:
        """
        按天拉取数据
        
        Args:
            start_date: 开始日期，格式 'YYYY-MM-DD'
            end_date: 结束日期，格式 'YYYY-MM-DD'
            interval_seconds: 每天内的间隔秒数（0 表示整天一次）
            debug: 是否打印调试信息
            **kwargs: 传递给 pull() 的其他参数
            
        Returns:
            PullResult 汇总结果
        """
        start_ts = time.time()
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        total_result = PullResult()
        current = start
        
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            day_start = f"{date_str} 00:00:00"
            day_end = f"{date_str} 23:59:59"
            
            if debug:
                debug_print(f"\n{'#'*50}")
                debug_print(f"# 处理日期: {date_str}")
                debug_print(f"{'#'*50}")
            
            try:
                if interval_seconds > 0:
                    result = self.pull_by_interval(
                        day_start, day_end, interval_seconds, 
                        debug=debug, **kwargs
                    )
                else:
                    result = self.pull(day_start, day_end, debug=debug, **kwargs)
                
                total_result.fetched += result.fetched
                total_result.saved += result.saved
                total_result.errors += result.errors
                
            except Exception as e:
                self.logger.error(f"处理 {date_str} 失败: {e}")
                total_result.errors += 1
            
            current += timedelta(days=1)
        
        total_result.duration = time.time() - start_ts
        return total_result
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(system={self.SYSTEM_NAME}, service={self.SERVICE_NAME})>"
