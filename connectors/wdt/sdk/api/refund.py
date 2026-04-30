#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
售后退款单相关API
"""

import time
from typing import Dict, Optional, List, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..client import QimenClient
from ..openapi_client import OpenAPIClient
from ..config import WdtConfig

# 日志模块（延迟导入避免循环依赖）
def _get_logger_funcs():
    try:
        from utils.logger import log_empty_pages, log_data_mismatch
        return log_empty_pages, log_data_mismatch
    except ImportError:
        return None, None

def _get_debug_print():
    """获取带时间戳的 debug_print 函数"""
    try:
        from utils.logger import debug_print
        return debug_print
    except ImportError:
        # 如果导入失败，返回普通 print
        return lambda msg, end='\n', flush=False: print(f"    {msg}", end=end, flush=flush)

def _get_task_queue_func():
    """获取任务队列入队函数"""
    try:
        from utils import TASK_QUEUE_AVAILABLE
        if TASK_QUEUE_AVAILABLE:
            from utils.task_queue import add_mismatch_task
            return add_mismatch_task
    except ImportError:
        pass
    return None


class RawRefundSearchAPI:
    """
    原始退款单搜索API
    
    用于搜索售后退款单数据
    API方法: wdt.aftersales.refund.rawrefund.search
    
    响应数据结构:
        - status: 状态码，0表示成功
        - message: 错误信息
        - data.order: 退款单列表
        - data.total_count: 总数量
    """
    
    METHOD = 'wdt.aftersales.refund.rawrefund.search'
    
    def __init__(self, client: Optional[QimenClient] = None,
                 config: Optional[WdtConfig] = None):
        """
        初始化API
        
        Args:
            client: 奇门客户端，为None时自动创建
            config: 配置对象，为None时使用默认配置
        """
        self.client = client or QimenClient(config)
    
    def search(self,
               start_time: str,
               end_time: str,
               time_type: int = 1,
               refund_no: Optional[str] = None,
               logistics_no: Optional[str] = None,
               platform_id: Optional[int] = None,
               shop_no: Optional[str] = None,
               tid: Optional[str] = None,
               oid: Optional[str] = None,
               detail_mask: int = 0,
               filter_detail: int = 0,
               page_size: int = 50,
               page_no: int = 1) -> Dict:
        """
        搜索原始退款单
        
        Args:
            start_time: 开始时间，格式：YYYY-MM-DD HH:MM:SS（必填）
            end_time: 结束时间，格式：YYYY-MM-DD HH:MM:SS（必填）
            time_type: 时间条件类型，1=修改时间，2=退款时间（默认1）
            refund_no: 原始退单号
            logistics_no: 物流单号
            platform_id: 平台id
            shop_no: 店铺编号（不支持批量查询）
            tid: 原始单号
            oid: 原始子单号
            detail_mask: 明细掩码，0=不返回优惠明细，1=返回优惠明细（默认0）
            filter_detail: 是否过滤明细，0=不过滤，1=只返回明细数据（默认0）
            page_size: 分页大小（建议200以下）
            page_no: 页号，从1开始
            
        Returns:
            查询结果:
                - status: 状态码，0表示成功
                - data.order: 退款单列表
                - data.total_count: 总数量
                
        退款单字段说明（order）:
            - refund_id: 原始退款单唯一id
            - refund_no: 原始退款单号
            - tid: 原始单号
            - oid: 原始子单号
            - shop_no: 店铺编号
            - shop_name: 店铺名称
            - type: 类型（1售前退款/2退货/3换货/4退款不退货）
            - status: 平台状态（1取消退款/2申请退款/3等待退货/4等待收货/5退款成功/7卖家拒绝退款）
            - process_status: 系统状态（0待递交/15已递交/20递交失败/40已处理）
            - refund_amount: 申请退款金额
            - actual_refund_amount: 实际退款金额
            - refund_time: 申请退款时间
            - reason: 退款原因
            - logistics_name: 物流公司名称
            - logistics_no: 物流单号
            - modified: 最后修改时间
            - detail_list: 原始退款单明细
            - discount_list: 原始退款单优惠明细
        """
        params = {
            'start_time': start_time,
            'end_time': end_time,
            'time_type': time_type
        }
        
        # 添加可选参数
        if refund_no:
            params['refund_no'] = refund_no
        if logistics_no:
            params['logistics_no'] = logistics_no
        if platform_id is not None:
            params['platform_id'] = platform_id
        if shop_no:
            params['shop_no'] = shop_no
        if tid:
            params['tid'] = tid
        if oid:
            params['oid'] = oid
        if detail_mask:
            params['detail_mask'] = detail_mask
        if filter_detail:
            params['filter_detail'] = filter_detail
        
        pager = {
            'page_size': page_size,
            'page_no': page_no
        }
        
        return self.client.call(self.METHOD, params, pager)
    
    def search_by_refund_no(self, refund_no: str) -> Dict:
        """
        根据退款单号查询
        
        Args:
            refund_no: 原始退款单号
            
        Returns:
            查询结果
        """
        # 需要传时间范围，使用较大范围
        return self.search(
            start_time='2020-01-01 00:00:00',
            end_time='2030-12-31 23:59:59',
            refund_no=refund_no
        )
    
    def search_by_time_range(self,
                             start_time: str,
                             end_time: str,
                             time_type: int = 1,
                             shop_no: Optional[str] = None,
                             with_discount: bool = False,
                             page_size: int = 50,
                             page_no: int = 1) -> Dict:
        """
        按时间范围查询退款单
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            time_type: 时间类型，1=修改时间，2=退款时间
            shop_no: 店铺编号（可选）
            with_discount: 是否返回优惠明细
            page_size: 分页大小
            page_no: 页号（从1开始）
            
        Returns:
            查询结果
        """
        return self.search(
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            shop_no=shop_no,
            detail_mask=1 if with_discount else 0,
            page_size=page_size,
            page_no=page_no
        )
    
    def search_all(self,
                   start_time: str,
                   end_time: str,
                   time_type: int = 1,
                   shop_no: Optional[str] = None,
                   with_discount: bool = False,
                   page_size: int = 50,
                   debug: bool = False,
                   max_workers: int = 10) -> List[Dict]:
        """
        搜索所有退款单（并行分页）
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            time_type: 时间类型，1=修改时间，2=退款时间
            shop_no: 店铺编号（可选）
            with_discount: 是否返回优惠明细
            page_size: 每页数量（建议200以下）
            debug: 是否打印调试信息
            max_workers: 并行线程数（默认10）
            
        Returns:
            所有退款单列表
        """
        debug_print = _get_debug_print()
        # 第一步：获取第一页，仅用于确定总数
        if debug:
            debug_print(f"    [DEBUG] 请求第 1 页（仅获取总数）...")
        
        first_result = self.search(
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            shop_no=shop_no,
            detail_mask=1 if with_discount else 0,
            page_size=page_size,
            page_no=1
        )
        
        status = first_result.get('status')
        if str(status) != '0':
            if debug:
                debug_print(f"    [DEBUG] API返回错误: status={status}, message={first_result.get('message')}")
            return []
        
        data = first_result.get('data', {})
        total_count = int(data.get('total_count', 0))
        
        if debug:
            debug_print(f"    [DEBUG] 总数: {total_count}, 每页: {page_size}")
        
        if total_count == 0:
            return []
        
        # 计算总页数
        total_pages = (total_count + page_size - 1) // page_size
        
        if debug:
            debug_print(f"    [DEBUG] 共 {total_pages} 页，从最后一页(第{total_pages}页)往前获取...")
        
        # 第二步：从最后一页往前并行获取（避免分页偏移）
        all_refunds = {}
        failed_pages = []
        
        def fetch_page(page_no):
            try:
                result = self.search(
                    start_time=start_time,
                    end_time=end_time,
                    time_type=time_type,
                    shop_no=shop_no,
                    detail_mask=1 if with_discount else 0,
                    page_size=page_size,
                    page_no=page_no
                )
                if str(result.get('status')) == '0':
                    refunds = result.get('data', {}).get('order', [])
                    return page_no, refunds, None
                return page_no, [], f"status={result.get('status')}"
            except Exception as e:
                return page_no, [], str(e)
        
        import time as _time
        empty_page_list = []  # 记录返回空数据的页码
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 从最后一页往前提交请求
            page_order = list(range(total_pages, 0, -1))
            futures = {executor.submit(fetch_page, p): p for p in page_order}
            
            completed = 0
            total_fetched = 0
            empty_pages = 0
            
            for future in as_completed(futures):
                page_no, refunds, error = future.result()
                if error:
                    failed_pages.append((page_no, error))
                else:
                    all_refunds[page_no] = refunds
                    if len(refunds) == 0:
                        empty_pages += 1
                        empty_page_list.append(page_no)
                    total_fetched += len(refunds)
                completed += 1
                if debug:
                    # 进度条显示
                    progress = completed / total_pages * 100
                    debug_print(f"\r    [DEBUG] 进度: {completed}/{total_pages} ({progress:.1f}%) | 已获取: {total_fetched} 条 | 空页: {empty_pages}    ", end='', flush=True)
            
            if debug:
                print()
        
        if debug:
            if failed_pages:
                debug_print(f"    [DEBUG] ⚠ {len(failed_pages)} 页请求失败")
                for p, err in failed_pages[:3]:
                    debug_print(f"      - 第{p}页: {err}")
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
                    _time.sleep(retry_delay)  # 串行请求间隔
                    _, refunds, error = fetch_page(page_no)
                    
                    if not error and len(refunds) > 0:
                        all_refunds[page_no] = refunds
                        recovered += 1
                        if debug:
                            debug_print(f"\r    [DEBUG] 重试第{retry_round+1}轮: 第{page_no}页恢复 {len(refunds)} 条", end='', flush=True)
                    else:
                        still_empty.append(page_no)
                
                if debug and recovered > 0:
                    print()
                    debug_print(f"    [DEBUG] 重试第{retry_round+1}轮完成: 恢复 {recovered} 页，剩余 {len(still_empty)} 页为空")
                
                empty_page_list = still_empty
            
            if debug and empty_page_list:
                debug_print(f"    [DEBUG] 重试后仍有 {len(empty_page_list)} 页为空: {sorted(empty_page_list)[:10]}...")
        
        # 记录空页日志
        log_empty_pages_func, log_data_mismatch_func = _get_logger_funcs()
        time_range = f"{start_time} ~ {end_time}"
        
        if log_empty_pages_func and empty_pages > 0:
            initial_empty = empty_pages
            recovered = initial_empty - len(empty_page_list) if empty_page_list else initial_empty
            log_empty_pages_func(
                api_name='raw_refund',
                time_range=time_range,
                empty_pages=list(range(initial_empty)),
                retry_recovered=recovered,
                still_empty=empty_page_list
            )
        
        # 按页码顺序合并结果
        result_list = []
        for page_no in sorted(all_refunds.keys()):
            result_list.extend(all_refunds[page_no])
        
        # 检查总数是否匹配并记录日志
        if log_data_mismatch_func and len(result_list) != total_count:
            log_data_mismatch_func(
                api_name='raw_refund',
                time_range=time_range,
                expected=total_count,
                actual=len(result_list),
                empty_pages=empty_page_list if empty_page_list else None,
                failed_pages=[p for p, _ in failed_pages] if failed_pages else None
            )
            # 加入重试队列
            add_task_func = _get_task_queue_func()
            if add_task_func:
                add_task_func('refund', start_time, end_time, total_count, len(result_list), shop_no=shop_no)
        
        if debug:
            debug_print(f"    [DEBUG] 并行获取完成，共 {len(result_list)} 条")
            if len(result_list) != total_count:
                debug_print(f"    [DEBUG] ⚠ 数据总数不匹配: 预期 {total_count}, 实际 {len(result_list)}")
        
        return result_list


# 退款类型常量
class RefundType:
    """退款类型"""
    PRE_SALE_REFUND = 1    # 售前退款
    RETURN_GOODS = 2        # 退货
    EXCHANGE = 3            # 换货
    REFUND_ONLY = 4         # 退款不退货


# 退款平台状态常量
class RefundPlatformStatus:
    """退款平台状态"""
    CANCELLED = 1           # 取消退款
    APPLIED = 2             # 申请退款
    WAIT_RETURN = 3         # 等待退货
    WAIT_RECEIVE = 4        # 等待收货
    SUCCESS = 5             # 退款成功
    REJECTED = 7            # 卖家拒绝退款


# 退款系统状态常量
class RefundProcessStatus:
    """退款系统状态"""
    WAIT_SUBMIT = 0         # 待递交
    SUBMITTED = 15          # 已递交
    SUBMIT_FAILED = 20      # 递交失败
    PROCESSED = 40          # 已处理


# 时间类型常量
class RefundTimeType:
    """时间查询类型"""
    MODIFIED_TIME = 1       # 修改时间
    REFUND_TIME = 2         # 退款时间


class AftersalesRefundSearchAPI:
    
    METHOD = 'wdt.aftersales.refund.refund.search'
    
    def __init__(self, client: Optional[Union[QimenClient, OpenAPIClient]] = None,
                 config: Optional[WdtConfig] = None):
        if client is None:
            self.client = QimenClient(config)
        elif isinstance(client, OpenAPIClient):
            self.client = QimenClient(client.config)
        else:
            self.client = client
    
    def search(self,
               start_time: str,
               end_time: str,
               time_type: int = 1,
               refund_no: Optional[str] = None,
               shop_no: Optional[str] = None,
               status: Optional[str] = None,
               page_size: int = 50,
               page_no: int = 1,
               debug: bool = False) -> Dict:
        params = {
            'modified_from': start_time,
            'modified_to': end_time
        }
        if shop_no:
            params['shop_nos'] = shop_no
        
        pager = {
            'page_size': page_size,
            'page_no': page_no
        }
        
        result = self.client.call(self.METHOD, params, pager, debug=debug)
        
        if debug:
            debug_print = _get_debug_print()
            status_code = result.get('status')
            data = result.get('data', {})
            total = data.get('total_count', 0)
            orders = data.get('order', [])
            debug_print(f"    [DEBUG] API响应: status={status_code}, total_count={total}, 本页={len(orders)}条")
        
        return result
    
    def search_all(self,
                   start_time: str,
                   end_time: str,
                   time_type: int = 1,
                   shop_no: Optional[str] = None,
                   status: Optional[str] = None,
                   page_size: int = 50,
                   debug: bool = False,
                   max_workers: int = 10) -> List[Dict]:
        debug_print = _get_debug_print()
        
        if debug:
            debug_print(f"    [DEBUG] 请求第 1 页（仅获取总数）...")
        
        first_result = self.search(
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            shop_no=shop_no,
            status=status,
            page_size=page_size,
            page_no=1,
            debug=debug
        )
        
        status_code = first_result.get('status')
        if str(status_code) != '0':
            if debug:
                debug_print(f"    [DEBUG] API返回错误: status={status_code}, message={first_result.get('message')}")
            return []
        
        data = first_result.get('data', {})
        total_count = int(data.get('total_count', 0))
        first_orders = data.get('order', [])
        
        if debug:
            debug_print(f"    [DEBUG] 总数: {total_count}, 每页: {page_size}")
        
        if total_count == 0:
            return []
        
        total_pages = (total_count + page_size - 1) // page_size
        
        if total_pages == 1:
            return first_orders
        
        all_refunds = {1: first_orders}
        
        def fetch_page(page_no):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = self.search(
                        start_time=start_time,
                        end_time=end_time,
                        time_type=time_type,
                        shop_no=shop_no,
                        status=status,
                        page_size=page_size,
                        page_no=page_no
                    )
                    if str(result.get('status')) == '0':
                        return page_no, result.get('data', {}).get('order', []), None
                    if attempt < max_retries - 1:
                        time.sleep(2 * (attempt + 1))
                        continue
                    return page_no, [], f"status={result.get('status')}"
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(2 * (attempt + 1))
                        continue
                    return page_no, [], str(e)

        actual_workers = min(max_workers, 5, total_pages - 1)
        with ThreadPoolExecutor(max_workers=actual_workers) as executor:
            page_order = list(range(2, total_pages + 1))
            futures = {executor.submit(fetch_page, p): p for p in page_order}
            failed_pages = []

            for future in as_completed(futures):
                page_no, refunds, error = future.result()
                if not error:
                    all_refunds[page_no] = refunds
                else:
                    failed_pages.append(page_no)
                    if debug:
                        debug_print(f"    [DEBUG] 第 {page_no} 页获取失败: {error}")

        if failed_pages:
            if debug:
                debug_print(f"    [DEBUG] 顺序补拉失败页: {failed_pages}")
            for page_no in failed_pages:
                time.sleep(1)
                _, refunds, error = fetch_page(page_no)
                if not error:
                    all_refunds[page_no] = refunds
                elif debug:
                    debug_print(f"    [DEBUG] 补拉第 {page_no} 页仍失败: {error}")

        result_list = []
        for page_no in sorted(all_refunds.keys()):
            result_list.extend(all_refunds[page_no])
        
        if debug:
            debug_print(f"    [DEBUG] 获取完成，共 {len(result_list)} 条 (期望 {total_count})")
        
        return result_list

