# -*- coding: utf-8 -*-
"""
客户详情拉取服务

从 external_user 表获取客户ID，调用 batch_get 接口获取详情，
将 follow_staffs 数据存入 follow_staff 表
"""

from typing import List, Dict

from common.base_service import BasePullService, PullResult
from ..client import WeibanClient, get_weiban_client
from ..repositories import ExternalUserRepository
from ..repositories.follow_staff_repo import FollowStaffRepository
from core.logger import get_logger


class ExternalUserDetailPullService(BasePullService):
    """
    客户详情拉取服务
    
    从 external_user 表获取所有客户ID，去重后批量调用 batch_get 接口，
    将每个客户的 follow_staffs 数据存入 follow_staff 表。
    
    唯一键：id + staff_id
    """
    
    SERVICE_NAME = 'external_user_detail'
    SYSTEM_NAME = 'weiban'
    API_NAME = 'external_user_batch_get'
    
    def __init__(self, client: WeibanClient = None,
                 external_user_repo: ExternalUserRepository = None,
                 follow_staff_repo: FollowStaffRepository = None):
        self.client = client or get_weiban_client()
        self.external_user_repo = external_user_repo or ExternalUserRepository()
        self.follow_staff_repo = follow_staff_repo or FollowStaffRepository()
        self.logger = get_logger(f'{self.SYSTEM_NAME}.{self.SERVICE_NAME}')
        
        # 不调用父类 __init__，因为我们有特殊的 repo 结构
        self.repo = self.follow_staff_repo
    
    def _fetch_data(self, start_time: str, end_time: str, **kwargs) -> List[Dict]:
        """兼容基类接口，实际不使用"""
        return []
    
    def pull_today(self, debug: bool = False, **kwargs) -> PullResult:
        """
        拉取客户详情数据
        
        流程：
        1. 从 external_user 表获取所有客户ID
        2. 去重后按20个一组调用 batch_get 接口
        3. 将每个客户的 follow_staffs 提取出来，附加 id 字段
        4. 存入 follow_staff 表（id + staff_id 作为唯一键）
        
        Args:
            debug: 是否打印调试信息
            **kwargs: 其他参数
                - max_workers: 并行线程数（默认5）
            
        Returns:
            PullResult 拉取结果
        """
        import time
        from core.logger import debug_print
        
        start_ts = time.time()
        result = PullResult()
        
        try:
            if debug:
                debug_print(f"\n[{self.SYSTEM_NAME}.{self.SERVICE_NAME}] 开始拉取客户详情...")
            
            # 1. 从 external_user 表获取所有客户ID
            if debug:
                debug_print(f"    从 external_user 表获取客户ID...")
            
            all_user_ids = self._get_user_ids_from_db()
            
            if not all_user_ids:
                if debug:
                    debug_print(f"    没有找到客户ID，请先拉取 external_user 数据")
                self.logger.warning("没有找到客户ID，请先拉取 external_user 数据")
                result.fetched = 0
                result.saved = 0
                return result
            
            if debug:
                debug_print(f"    获取到 {len(all_user_ids)} 个客户ID（去重后）")
            
            # 2. 调用 batch_get 接口获取详情
            if debug:
                debug_print(f"    调用 batch_get 接口获取详情...")
            
            max_workers = kwargs.get('max_workers', 5)
            all_users = self.client.external_user_api.batch_get_all(
                list(all_user_ids),
                debug=debug,
                max_workers=max_workers
            )
            
            if not all_users:
                if debug:
                    debug_print(f"    batch_get 未返回数据")
                result.fetched = 0
                result.saved = 0
                return result
            
            if debug:
                debug_print(f"    获取到 {len(all_users)} 个客户详情")
            
            # 3. 提取 follow_staffs 数据
            if debug:
                debug_print(f"    提取 follow_staffs 数据...")
            
            follow_staff_list = []
            for user in all_users:
                user_id = user.get('id', '')
                follow_staffs = user.get('follow_staffs', [])
                
                if not user_id or not follow_staffs:
                    continue
                
                for staff in follow_staffs:
                    if isinstance(staff, dict):
                        # 复制员工关系数据，并添加客户ID
                        staff_data = staff.copy()
                        staff_data['id'] = user_id
                        
                        # 也添加客户的基本信息
                        staff_data['user_name'] = user.get('name', '')
                        staff_data['user_avatar'] = user.get('avatar', '')
                        staff_data['user_gender'] = user.get('gender')
                        staff_data['user_type'] = user.get('type')
                        staff_data['unionid'] = user.get('unionid', '')
                        
                        follow_staff_list.append(staff_data)
            
            result.fetched = len(follow_staff_list)
            
            if debug:
                debug_print(f"    提取到 {result.fetched} 条客户-员工关系数据")
            
            # 4. 存入数据库
            if follow_staff_list:
                if debug:
                    debug_print(f"    保存数据到数据库...")
                
                saved = self.follow_staff_repo.save_batch(
                    follow_staff_list, 
                    batch_size=500,
                    debug=debug
                )
                result.saved = saved
                
                if debug:
                    debug_print(f"    保存完成: {saved} 条")
            
            result.errors = max(0, result.fetched - result.saved)
            
        except Exception as e:
            if debug:
                debug_print(f"    [ERROR] 拉取失败: {e}")
            self.logger.error(f"拉取失败: {e}", exc_info=True)
            result.errors = 1
            result.details['error'] = str(e)
        
        result.duration = time.time() - start_ts
        
        if debug:
            debug_print(f"\n[{self.SYSTEM_NAME}.{self.SERVICE_NAME}] 拉取完成")
            debug_print(f"    获取: {result.fetched} 条")
            debug_print(f"    保存: {result.saved} 条")
            debug_print(f"    耗时: {result.duration:.2f} 秒")
        
        return result
    
    def _get_user_ids_from_db(self) -> set:
        """从 external_user 表获取所有客户ID"""
        table_name = self.external_user_repo.full_table_name
        
        # 检查表是否存在
        check_sql = f"""
            SELECT COUNT(*) as cnt FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = '{table_name}'
        """
        result = self.external_user_repo.db.fetch_one(check_sql)
        
        if not result or result['cnt'] == 0:
            return set()
        
        # 获取所有客户ID
        sql = f"SELECT DISTINCT `id` FROM `{table_name}`"
        rows = self.external_user_repo.db.fetch_all(sql)
        
        return {str(row['id']).strip() for row in rows if row.get('id')}
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            'total_records': self.follow_staff_repo.count(),
            'unique_users': len(self.follow_staff_repo.get_all_user_ids()),
        }

