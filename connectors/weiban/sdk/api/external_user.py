# -*- coding: utf-8 -*-
"""
客户管理相关 API

根据时间获取添加客户列表
"""

from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..client import WeibanAPIClient
from ..config import WeibanConfig


def _get_debug_print():
    """获取带时间戳的 debug_print 函数"""
    try:
        from utils.logger import debug_print
        return debug_print
    except ImportError:
        # 如果导入失败，返回普通 print
        return lambda msg, end='\n', flush=False: print(f"    {msg}", end=end, flush=flush)


class ExternalUserAPI:
    """
    客户管理 API
    
    API 端点: /open-api/external_user_staff_relation/list
    
    响应数据结构:
        - errcode: 状态码，0为正常
        - errmsg: 错误信息
        - external_user_list: 客户列表
        - total: 总数
    """
    
    ENDPOINT = '/open-api/external_user_staff_relation/list'
    
    def __init__(self, client: Optional[WeibanAPIClient] = None,
                 config: Optional[WeibanConfig] = None):
        """
        初始化 API
        
        Args:
            client: API 客户端，为 None 时自动创建
            config: 配置对象
        """
        self.client = client or WeibanAPIClient(config)
    
    def list(self,
             start_add_time: Optional[str] = None,
             end_add_time: Optional[str] = None,
             limit: int = 100,
             offset: int = 0,
             staff_id: Optional[str] = None,
             outflow: Optional[int] = None,
             debug: bool = False) -> Dict:
        """
        获取添加客户列表
        
        Args:
            start_add_time: 起始时间（时间戳字符串）
            end_add_time: 截止时间（时间戳字符串）
            limit: 返回数量，默认30，最大100
            offset: 列表偏移，默认0
            staff_id: 员工的id
            outflow: 1-已流失，0-未流失
            debug: 是否打印调试信息
            
        Returns:
            API 响应:
                - errcode: 状态码
                - errmsg: 错误信息
                - external_user_list: 客户列表
                - total: 总数
                
        客户对象字段说明 (external_user_list):
            - id: 客户 external_id
            - name: 客户昵称
            - avatar: 头像链接
            - gender: 性别
            - type: 外部联系人类型（1=微信用户，2=企业微信用户）
            - corp_name: 企业名称
            - corp_full_name: 企业全称
            - position: 职位
            - score: 客户评分
            - unionid: 微信 unionid
            - created_at: 入库时间
            - updated_at: 更新时间
            - staff_relation: 员工客户关系
                - staff_id: 员工id
                - add_time: 员工添加时间
                - remark: 备注
        """
        params = {
            'limit': min(limit, 100),
            'offset': offset,
        }
        
        if start_add_time:
            params['start_add_time'] = start_add_time
        if end_add_time:
            params['end_add_time'] = end_add_time
        if staff_id:
            params['staff_id'] = staff_id
        if outflow is not None:
            params['outflow'] = outflow
        
        return self.client.get(self.ENDPOINT, params, debug=debug)
    
    def list_all(self,
                 start_add_time: Optional[str] = None,
                 end_add_time: Optional[str] = None,
                 staff_id: Optional[str] = None,
                 outflow: Optional[int] = None,
                 limit: int = 100,
                 debug: bool = False,
                 max_workers: int = 10) -> List[Dict]:
        """
        获取所有客户（自动分页，支持并行）
        
        Args:
            start_add_time: 起始时间（时间戳字符串）
            end_add_time: 截止时间（时间戳字符串）
            staff_id: 员工id
            outflow: 1-已流失，0-未流失，None-所有客户（默认）
            limit: 每页数量（最大100）
            debug: 是否打印调试信息
            max_workers: 并行线程数（默认10）
            
        Returns:
            所有客户列表
        """
        debug_print = _get_debug_print()
        import time as _time
        
        # 第一步：获取第一页，确定总数
        if debug:
            debug_print(f"    [DEBUG] 请求第 1 页（仅获取总数）...")
            if staff_id:
                debug_print(f"    [DEBUG] 员工ID: {staff_id}")
            if outflow is not None:
                debug_print(f"    [DEBUG] 流失状态: {'已流失' if outflow == 1 else '未流失'}")
            else:
                debug_print(f"    [DEBUG] 流失状态: 所有客户（不区分流失状态）")
        
        _start = _time.time()
        first_result = self.list(
            start_add_time=start_add_time,
            end_add_time=end_add_time,
            limit=limit,
            offset=0,
            staff_id=staff_id,
            outflow=outflow,
            debug=False
        )
        
        if debug:
            debug_print(f"    [DEBUG] 响应耗时: {_time.time() - _start:.2f}秒")
        
        # 检查响应状态
        if first_result.get('errcode') != 0:
            if debug:
                debug_print(f"    [DEBUG] API 错误: {first_result.get('errmsg')}")
            return []
        
        users = first_result.get('external_user_list', [])
        total = first_result.get('total', 0)
        
        if debug:
            debug_print(f"    [DEBUG] 总数: {total}, 每页: {limit}")
        
        if total == 0:
            return []
        
        # 计算总页数（offset 从 0 开始，所以总页数 = (total + limit - 1) // limit）
        total_pages = (total + limit - 1) // limit
        
        if debug:
            debug_print(f"    [DEBUG] 共 {total_pages} 页，使用 {max_workers} 个线程并行获取...")
        
        # 如果只有一页，直接返回
        if total_pages == 1:
            return users
        
        # 第二步：并行获取所有页
        all_users_dict = {}  # 用字典保存，key 是 offset
        failed_pages = []
        
        def fetch_page(page_offset):
            """获取指定 offset 的页面"""
            try:
                result = self.list(
                    start_add_time=start_add_time,
                    end_add_time=end_add_time,
                    limit=limit,
                    offset=page_offset,
                    staff_id=staff_id,
                    outflow=outflow,
                    debug=False
                )
                if result.get('errcode') == 0:
                    users = result.get('external_user_list', [])
                    return page_offset, users, None
                return page_offset, [], f"errcode={result.get('errcode')}, errmsg={result.get('errmsg')}"
            except Exception as e:
                return page_offset, [], str(e)
        
        empty_page_list = []  # 记录返回空数据的页码
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 生成所有页的 offset（0, limit, 2*limit, ...）
            offsets = [i * limit for i in range(total_pages)]
            # 从后往前提交请求（避免新数据插入导致分页偏移）
            offsets.reverse()
            futures = {executor.submit(fetch_page, offset): offset for offset in offsets}
            
            completed = 0
            total_fetched = 0
            empty_pages = 0
            
            for future in as_completed(futures):
                page_offset, users, error = future.result()
                if error:
                    failed_pages.append((page_offset, error))
                else:
                    all_users_dict[page_offset] = users
                    if len(users) == 0:
                        empty_pages += 1
                        empty_page_list.append(page_offset // limit + 1)  # 页码从1开始
                    total_fetched += len(users)
                completed += 1
                if debug:
                    # 进度条显示
                    progress = completed / total_pages * 100
                    avg_per_page = total_fetched / completed if completed > 0 else 0
                    debug_print(f"\r    [DEBUG] 进度: {completed}/{total_pages} ({progress:.1f}%) | 已获取: {total_fetched} 条 | 平均: {avg_per_page:.1f}条/页 | 空页: {empty_pages}    ", 
                               end='', flush=True)
            
            if debug:
                print()  # 换行
        
        if debug:
            if failed_pages:
                debug_print(f"    [DEBUG] ⚠ {len(failed_pages)} 页请求失败")
                for offset, err in failed_pages[:3]:
                    page_no = offset // limit + 1
                    debug_print(f"      - 第{page_no}页 (offset={offset}): {err}")
            if empty_pages > 0:
                debug_print(f"    [DEBUG] ⚠ {empty_pages} 页返回空数据（API可能有并发限制）")
        
        # 空页重试：对返回空数据的页面进行串行重试
        if empty_page_list:
            max_retry = 3  # 最大重试次数
            retry_delay = 0.5  # 重试间隔（秒）
            
            if debug:
                debug_print(f"    [DEBUG] 开始空页重试，共 {len(empty_page_list)} 页需要重试...")
            
            for retry_round in range(max_retry):
                if not empty_page_list:
                    break
                
                still_empty = []
                recovered = 0
                
                for page_no in empty_page_list:
                    page_offset = (page_no - 1) * limit
                    _time.sleep(retry_delay)  # 串行请求间隔
                    _, users, error = fetch_page(page_offset)
                    
                    if not error and len(users) > 0:
                        all_users_dict[page_offset] = users
                        recovered += 1
                        if debug:
                            debug_print(f"\r    [DEBUG] 重试第{retry_round+1}轮: 第{page_no}页恢复 {len(users)} 条", 
                                       end='', flush=True)
                    else:
                        still_empty.append(page_no)
                
                if debug and recovered > 0:
                    print()
                    debug_print(f"    [DEBUG] 重试第{retry_round+1}轮完成: 恢复 {recovered} 页，剩余 {len(still_empty)} 页为空")
                
                empty_page_list = still_empty
            
            if debug and empty_page_list:
                debug_print(f"    [DEBUG] 重试后仍有 {len(empty_page_list)} 页为空: {sorted(empty_page_list)[:10]}...")
        
        # 按 offset 顺序合并结果
        result_list = []
        for offset in sorted(all_users_dict.keys()):
            result_list.extend(all_users_dict[offset])
        
        if debug:
            debug_print(f"    [DEBUG] 并行获取完成，共 {len(result_list)} 条")
            if len(result_list) != total:
                debug_print(f"    [DEBUG] ⚠ 数据总数不匹配: 预期 {total}, 实际 {len(result_list)}")
        
        return result_list
    
    def list_not_outflow(self, 
                         staff_id: Optional[str] = None,
                         debug: bool = False,
                         max_workers: int = 10) -> List[Dict]:
        """
        获取所有未流失客户（实时接口，支持并行）
        
        注意：微伴接口是实时的，不按时间范围过滤，总是返回当前所有未流失客户。
        
        Args:
            staff_id: 员工ID（可选，用于过滤特定员工的客户）
            debug: 调试模式
            max_workers: 并行线程数（默认10）
            
        Returns:
            未流失客户列表
        """
        return self.list_all(
            staff_id=staff_id,
            outflow=0,
            debug=debug,
            max_workers=max_workers
        )
    
    def list_outflow(self,
                     staff_id: Optional[str] = None,
                     debug: bool = False,
                     max_workers: int = 10) -> List[Dict]:
        """
        获取所有已流失客户（实时接口，支持并行）
        
        注意：微伴接口是实时的，不按时间范围过滤，总是返回当前所有已流失客户。
        
        Args:
            staff_id: 员工ID（可选，用于过滤特定员工的客户）
            debug: 调试模式
            max_workers: 并行线程数（默认10）
            
        Returns:
            已流失客户列表
        """
        return self.list_all(
            staff_id=staff_id,
            outflow=1,
            debug=debug,
            max_workers=max_workers
        )
    
    def batch_get(self, id_list: List[str], debug: bool = False) -> Dict:
        """
        批量获取客户详情
        
        API 端点: POST /open-api/external_user/batch_get
        
        Args:
            id_list: 客户ID列表，最多20个
            debug: 是否打印调试信息
            
        Returns:
            API 响应:
                - errcode: 状态码
                - errmsg: 错误信息
                - external_user: 客户详情列表
                - total: 总数
        """
        if len(id_list) > 20:
            raise ValueError("批量查询最多支持20个客户ID")
        
        return self.client.post(
            '/open-api/external_user/batch_get',
            {'id_list': id_list},
            debug=debug
        )
    
    def batch_get_all(self, id_list: List[str], debug: bool = False, 
                      max_workers: int = 5) -> List[Dict]:
        """
        批量获取所有客户详情（自动分组，支持并行）
        
        Args:
            id_list: 客户ID列表（不限数量，自动按20个分组）
            debug: 是否打印调试信息
            max_workers: 并行线程数（默认5，避免API限流）
            
        Returns:
            所有客户详情列表
        """
        import time as _time
        debug_print = _get_debug_print()
        
        if not id_list:
            return []
        
        # 去重
        unique_ids = list(set(id_list))
        total_ids = len(unique_ids)
        
        if debug:
            debug_print(f"    [DEBUG] 批量获取客户详情，共 {total_ids} 个ID（去重后）")
        
        # 按20个一组分组
        batch_size = 20
        batches = [unique_ids[i:i+batch_size] for i in range(0, total_ids, batch_size)]
        total_batches = len(batches)
        
        if debug:
            debug_print(f"    [DEBUG] 分为 {total_batches} 组，使用 {max_workers} 个线程并行获取...")
        
        all_users = []
        failed_batches = []
        
        def fetch_batch(batch_idx, batch_ids):
            """获取一批客户详情"""
            try:
                result = self.batch_get(batch_ids, debug=False)
                if result.get('errcode') == 0:
                    users = result.get('external_user', [])
                    return batch_idx, users, None
                return batch_idx, [], f"errcode={result.get('errcode')}, errmsg={result.get('errmsg')}"
            except Exception as e:
                return batch_idx, [], str(e)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(fetch_batch, idx, batch): idx 
                for idx, batch in enumerate(batches)
            }
            
            completed = 0
            total_fetched = 0
            
            for future in as_completed(futures):
                batch_idx, users, error = future.result()
                if error:
                    failed_batches.append((batch_idx, error))
                else:
                    all_users.extend(users)
                    total_fetched += len(users)
                completed += 1
                
                if debug:
                    progress = completed / total_batches * 100
                    debug_print(f"\r    [DEBUG] 进度: {completed}/{total_batches} ({progress:.1f}%) | 已获取: {total_fetched} 条    ", 
                               end='', flush=True)
            
            if debug:
                print()
        
        # 重试失败的批次
        if failed_batches:
            if debug:
                debug_print(f"    [DEBUG] {len(failed_batches)} 批请求失败，开始重试...")
            
            for batch_idx, _ in failed_batches:
                _time.sleep(0.5)  # 重试间隔
                _, users, error = fetch_batch(batch_idx, batches[batch_idx])
                if not error:
                    all_users.extend(users)
                    if debug:
                        debug_print(f"    [DEBUG] 第{batch_idx+1}批重试成功，获取 {len(users)} 条")
        
        if debug:
            debug_print(f"    [DEBUG] 批量获取完成，共 {len(all_users)} 条客户详情")
        
        return all_users

