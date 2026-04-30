# -*- coding: utf-8 -*-
"""
客户数据拉取服务

实现从微伴 API 拉取客户数据并保存到数据库
"""

from typing import List, Dict, Union, Optional

from common.base_service import BasePullService, PullResult
from ..client import WeibanClient, get_weiban_client
from ..repositories import ExternalUserRepository
from core.config import get_config

# 延迟导入，避免缺少 pymssql 时无法启动
try:
    from ..utils.ehr_db import get_staff_ids_from_ehr
    EHR_DB_AVAILABLE = True
except ImportError:
    EHR_DB_AVAILABLE = False
    def get_staff_ids_from_ehr(*args, **kwargs):
        raise RuntimeError("缺少 pymssql 库，无法从 EHR 数据库读取员工ID。请安装: pip install pymssql")


class ExternalUserPullService(BasePullService):
    """
    客户数据拉取服务
    
    从微伴拉取客户数据并保存到数据库，实现特殊的对比逻辑：
    - 新增客户自动设置 join_time
    - 流失客户自动更新 outflow_time
    """
    
    SERVICE_NAME = 'external_user'
    SYSTEM_NAME = 'weiban'
    API_NAME = 'external_user_list'
    
    def __init__(self, client: WeibanClient = None, 
                 repository: ExternalUserRepository = None):
        self.client = client or get_weiban_client()
        self.repo = repository or ExternalUserRepository()
        super().__init__(self.client, self.repo)
    
    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        """
        从 API 获取客户数据
        
        注意：微伴接口是实时的，不按时间范围过滤，返回当前所有客户（包括已流失和未流失）。
        此方法主要用于兼容基类接口，实际应使用 pull_today()。
        
        Args:
            start_time: 开始时间（忽略，仅用于兼容）
            end_time: 结束时间（忽略，仅用于兼容）
            **kwargs: 其他参数
                - staff_id: 员工ID
                - debug: 调试模式
                - max_workers: 并行线程数
                
        Returns:
            客户数据列表
        """
        # 微伴接口是实时的，不传递时间参数和流失状态参数（获取所有客户）
        return self.client.external_user_api.list_all(
            staff_id=kwargs.get('staff_id'),
            debug=kwargs.get('debug', False),
            max_workers=kwargs.get('max_workers', 10)
        )
    
    def pull_today(self, debug: bool = False, **kwargs) -> PullResult:
        """
        拉取当前客户数据（实时接口）
        
        微伴接口是实时的，返回当前所有客户（包括已流失和未流失）。
        此方法会自动处理：
        1. 获取当前所有客户（实时数据，不区分流失状态）
        2. 与数据库对比，标记新加入和流失的客户
        
        Args:
            debug: 是否打印调试信息
            **kwargs: 其他参数
                - staff_id: 单个员工ID（可选，与 staff_ids 二选一）
                - staff_ids: 员工ID列表（可选，与 staff_id 二选一）
                - max_workers: 并行线程数（可选）
            
        Returns:
            PullResult 拉取结果（包含额外的统计信息）
        """
        import time
        from core.logger import debug_print
        
        start_ts = time.time()
        result = PullResult()
        
        try:
            # 处理员工ID参数：支持单个ID或ID列表，或从数据库读取
            staff_id = kwargs.get('staff_id')
            staff_ids = kwargs.get('staff_ids')
            use_ehr = kwargs.get('use_ehr', True)  # 默认从 EHR 数据库读取
            
            # 如果提供了 staff_ids，转换为列表
            if staff_ids:
                if isinstance(staff_ids, str):
                    # 如果是逗号分隔的字符串，转换为列表
                    staff_ids = [s.strip() for s in staff_ids.split(',') if s.strip()]
                elif not isinstance(staff_ids, list):
                    staff_ids = [staff_ids]
            elif staff_id:
                # 如果只提供了单个 staff_id，转换为列表
                staff_ids = [staff_id]
            elif use_ehr and EHR_DB_AVAILABLE:
                # 都没有提供，且允许从 EHR 读取，则从数据库读取员工ID列表
                try:
                    config = get_config()
                    weiban_config = config.get_connector_config('weiban') or {}
                    ehr_config = weiban_config.get('ehr_database')
                    
                    if ehr_config:
                        if debug:
                            debug_print(f"    从 EHR 数据库读取员工ID列表...")
                        staff_ids = get_staff_ids_from_ehr(ehr_config)
                        if debug:
                            debug_print(f"    从 EHR 数据库获取到 {len(staff_ids)} 个员工ID")
                    else:
                        if debug:
                            debug_print(f"    警告: 未配置 EHR 数据库，将拉取全量数据")
                        staff_ids = None
                except Exception as e:
                    if debug:
                        debug_print(f"    [ERROR] 从 EHR 数据库读取员工ID失败: {e}")
                    self.logger.warning(f"从 EHR 数据库读取员工ID失败: {e}，将拉取全量数据")
                    staff_ids = None
            elif use_ehr and not EHR_DB_AVAILABLE:
                if debug:
                    debug_print(f"    警告: 缺少 pymssql 库，无法从 EHR 数据库读取，将拉取全量数据")
                self.logger.warning("缺少 pymssql 库，无法从 EHR 数据库读取员工ID，将拉取全量数据")
                staff_ids = None
            else:
                # 都没有提供，且不允许从 EHR 读取，拉取全量
                staff_ids = None
            
            if debug:
                debug_print(f"\n[{self.SYSTEM_NAME}.{self.SERVICE_NAME}] 开始拉取客户数据...")
                if staff_ids:
                    debug_print(f"    员工ID列表: {staff_ids} (共 {len(staff_ids)} 个员工)")
                else:
                    debug_print(f"    拉取模式: 全量（所有员工）")
            
            # 如果指定了员工ID列表，循环拉取每个员工的数据
            if staff_ids:
                all_data = []
                total_staffs = len(staff_ids)
                
                for idx, sid in enumerate(staff_ids, 1):
                    if debug:
                        debug_print(f"\n    处理员工 {idx}/{total_staffs}: {sid}")
                    
                    try:
                        # 获取该员工的客户数据
                        staff_data = self.client.external_user_api.list_all(
                            staff_id=sid,
                            debug=debug,
                            max_workers=kwargs.get('max_workers', 10)
                        )
                        
                        if staff_data:
                            all_data.extend(staff_data)
                            if debug:
                                debug_print(f"        员工 {sid}: 获取 {len(staff_data)} 条客户数据")
                    except Exception as e:
                        if debug:
                            debug_print(f"        [ERROR] 员工 {sid} 拉取失败: {e}")
                        self.logger.error(f"员工 {sid} 拉取失败: {e}")
                        result.errors += 1
                        continue
                
                data = all_data
                if debug:
                    debug_print(f"\n    所有员工数据合并完成，共 {len(data)} 条")
            else:
                # 全量拉取（不指定员工ID）
                data = self.client.external_user_api.list_all(
                    staff_id=None,
                    debug=debug,
                    max_workers=kwargs.get('max_workers', 10)
                )
            
            result.fetched = len(data) if data else 0
            
            if debug:
                debug_print(f"    从 API 获取 {result.fetched} 条客户数据")
            
            # 使用特殊的对比保存逻辑
            if data and self.repo:
                if debug:
                    debug_print(f"    开始保存数据到数据库...")
                
                save_result = self.repo.save_with_comparison(data, debug=debug)
                result.saved = save_result['saved']
                result.details['new_joined'] = save_result['new_joined']
                result.details['outflow_marked'] = save_result['outflow_marked']
                
                if debug:
                    debug_print(f"    保存完成: {result.saved} 条")
                    debug_print(f"    新加入: {save_result['new_joined']} 条")
                    debug_print(f"    标记流失: {save_result['outflow_marked']} 条")
            elif data:
                result.saved = result.fetched
            
            result.errors = max(0, result.fetched - result.saved)
            
        except Exception as e:
            if debug:
                debug_print(f"    [ERROR] 拉取失败: {e}")
            self.logger.error(f"拉取失败: {e}")
            result.errors = 1
            result.details['error'] = str(e)
        
        result.duration = time.time() - start_ts
        
        if debug:
            debug_print(f"\n[{self.SYSTEM_NAME}.{self.SERVICE_NAME}] 拉取完成")
            debug_print(f"    获取: {result.fetched} 条")
            debug_print(f"    保存: {result.saved} 条")
            debug_print(f"    新加入: {result.details.get('new_joined', 0)} 条")
            debug_print(f"    标记流失: {result.details.get('outflow_marked', 0)} 条")
            debug_print(f"    耗时: {result.duration:.2f} 秒")
        
        return result
    
    
    def get_statistics(self) -> Dict:
        """
        获取客户统计信息
        
        Returns:
            统计信息字典:
                - total: 总客户数
                - active: 未流失客户数
                - outflow: 已流失客户数
        """
        return {
            'total': self.repo.count(),
            'active': self.repo.count_active(),
            'outflow': self.repo.count_outflow(),
        }

