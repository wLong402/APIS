#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
入库单相关API
"""

from typing import Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..client import QimenClient
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


class StockinRefundQueryAPI:
    """
    退货入库单查询API（带明细）
    
    用于查询ERP退货入库单信息
    API方法: wdt.wms.stockin.refund.querywithdetail
    
    响应数据结构:
        - status: 状态码，0表示成功
        - message: 错误信息
        - data.order: 入库单列表
        - data.total_count: 总数量
    """
    
    # API方法名
    METHOD = 'wdt.wms.stockin.refund.querywithdetail'
    
    def __init__(self, client: Optional[QimenClient] = None, 
                 config: Optional[WdtConfig] = None):
        """
        初始化API
        
        Args:
            client: 奇门客户端，为None时自动创建
            config: 配置对象，为None时使用默认配置
        """
        self.client = client or QimenClient(config)
    
    def query(self, 
              start_time: str,
              end_time: str,
              time_type: int = 1,
              status: Optional[str] = None,
              warehouse_no: Optional[str] = None,
              shop_no: Optional[str] = None,
              stockin_no: Optional[str] = None,
              src_order_no: Optional[str] = None,
              refund_no: Optional[str] = None,
              logistics_no: Optional[str] = None,
              page_size: int = 50,
              page_no: int = 1,
              debug: bool = False) -> Dict:
        """
        查询退货入库单
        
        Args:
            start_time: 开始时间，格式：YYYY-MM-DD HH:MM:SS（必填）
            end_time: 结束时间，格式：YYYY-MM-DD HH:MM:SS（必填）
            time_type: 时间类型（默认1）
                - 1: 修改时间
                - 2: 入库时间
                - 3: 创建时间
            status: 入库单状态，多个状态用逗号分隔（可选）
                - 5: 已取消
                - 10: 待质检
                - 15: 质检中
                - 20: 待签收
                - 50: 待审核
                - 60: 待入库
                - 65: 待处理
                - 70: 入库中
                - 80: 待过账
                - 110: 已完成
            warehouse_no: 仓库编号（可选）
            shop_no: 店铺编号（可选）
            stockin_no: 入库单号（可选）
            src_order_no: 系统订单号（可选）
            refund_no: 退款单号（可选）
            logistics_no: 物流单号（可选）
            page_size: 每页数量（默认50，建议200以下）
            page_no: 页码（从1开始）
            debug: 是否打印调试信息
            
        Returns:
            查询结果，包含：
                - status: 状态码，0表示成功
                - data.order: 入库单列表
                - data.total_count: 总数量
                
        入库单字段说明（order）:
            - stockin_id: 入库单唯一ID
            - stockin_no: 入库单号
            - src_order_no: 系统订单号
            - refund_no: 退款单号
            - shop_no: 店铺编号
            - shop_name: 店铺名称
            - warehouse_no: 仓库编号
            - warehouse_name: 仓库名称
            - status: 入库单状态
            - stockin_time: 入库时间
            - created: 创建时间
            - modified: 修改时间
            - logistics_name: 物流公司
            - logistics_no: 物流单号
            - receiver_name: 收货人
            - receiver_mobile: 收货人手机
            - remark: 备注
            - detail_list: 明细列表
        """
        params = {
            'start_time': start_time,
            'end_time': end_time,
            'time_type': time_type
        }
        
        if status is not None:
            params['status'] = status
        if warehouse_no:
            params['warehouse_no'] = warehouse_no
        if shop_no:
            params['shop_no'] = shop_no
        if stockin_no:
            params['stockin_no'] = stockin_no
        if src_order_no:
            params['src_order_no'] = src_order_no
        if refund_no:
            params['refund_no'] = refund_no
        if logistics_no:
            params['logistics_no'] = logistics_no
        
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
            debug_print(f"[DEBUG] API响应: status={status_code}, total_count={total}, 本页={len(orders)}条")
        
        return result
    
    def query_by_stockin_no(self, stockin_no: str) -> Dict:
        """
        根据入库单号查询
        
        Args:
            stockin_no: 入库单号
            
        Returns:
            查询结果
        """
        return self.query(
            start_time='2020-01-01 00:00:00',
            end_time='2030-12-31 23:59:59',
            stockin_no=stockin_no
        )
    
    def query_by_refund_no(self, refund_no: str) -> Dict:
        """
        根据退款单号查询
        
        Args:
            refund_no: 退款单号
            
        Returns:
            查询结果
        """
        return self.query(
            start_time='2020-01-01 00:00:00',
            end_time='2030-12-31 23:59:59',
            refund_no=refund_no
        )
    
    def query_by_logistics_no(self, logistics_no: str) -> Dict:
        """
        根据物流单号查询
        
        Args:
            logistics_no: 物流单号
            
        Returns:
            查询结果
        """
        return self.query(
            start_time='2020-01-01 00:00:00',
            end_time='2030-12-31 23:59:59',
            logistics_no=logistics_no
        )
    
    def query_all(self,
                  start_time: str,
                  end_time: str,
                  time_type: int = 1,
                  status: Optional[str] = None,
                  warehouse_no: Optional[str] = None,
                  shop_no: Optional[str] = None,
                  page_size: int = 50,
                  debug: bool = False,
                  max_workers: int = 10) -> List[Dict]:
        """
        查询所有退货入库单（并行分页）
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            time_type: 时间类型（1=修改时间, 2=入库时间, 3=创建时间）
            status: 入库单状态（可选）
            warehouse_no: 仓库编号（可选）
            shop_no: 店铺编号（可选）
            page_size: 每页数量（建议200以下）
            debug: 是否打印调试信息
            max_workers: 并行线程数（默认10）
            
        Returns:
            所有入库单列表
        """
        debug_print = _get_debug_print()
        
        # 第一步：获取第一页，仅用于确定总数
        if debug:
            debug_print(f"[DEBUG] 请求第 1 页（仅获取总数）...")
            debug_print(f"[DEBUG] 参数: start_time={start_time}, end_time={end_time}, time_type={time_type}")
        
        import time as _time
        _start = _time.time()
        
        first_result = self.query(
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            status=status,
            warehouse_no=warehouse_no,
            shop_no=shop_no,
            page_size=page_size,
            page_no=1,
            debug=debug
        )
        
        if debug:
            debug_print(f"[DEBUG] 响应耗时: {_time.time() - _start:.2f}秒")
        
        status_code = first_result.get('status')
        if str(status_code) != '0':
            if debug:
                debug_print(f"[DEBUG] API返回错误: status={status_code}, message={first_result.get('message')}")
            return []
        
        data = first_result.get('data', {})
        total_count = int(data.get('total_count', 0))
        
        if debug:
            debug_print(f"[DEBUG] 总数: {total_count}, 每页: {page_size}")
        
        if total_count == 0:
            return []
        
        # 计算总页数
        total_pages = (total_count + page_size - 1) // page_size
        
        if debug:
            debug_print(f"[DEBUG] 共 {total_pages} 页，从最后一页(第{total_pages}页)往前获取...")
        
        # 第二步：从最后一页往前并行获取（避免分页偏移）
        all_stockins = {}
        failed_pages = []
        
        def fetch_page(page_no):
            try:
                result = self.query(
                    start_time=start_time,
                    end_time=end_time,
                    time_type=time_type,
                    status=status,
                    warehouse_no=warehouse_no,
                    shop_no=shop_no,
                    page_size=page_size,
                    page_no=page_no
                )
                if str(result.get('status')) == '0':
                    stockins = result.get('data', {}).get('order', [])
                    return page_no, stockins, None
                return page_no, [], f"status={result.get('status')}, msg={result.get('message')}"
            except Exception as e:
                return page_no, [], str(e)
        
        empty_page_list = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 从最后一页往前提交请求
            page_order = list(range(total_pages, 0, -1))
            futures = {executor.submit(fetch_page, p): p for p in page_order}
            
            completed = 0
            total_fetched = 0
            empty_pages = 0
            
            for future in as_completed(futures):
                page_no, stockins, error = future.result()
                if error:
                    failed_pages.append((page_no, error))
                else:
                    all_stockins[page_no] = stockins
                    if len(stockins) == 0:
                        empty_pages += 1
                        empty_page_list.append(page_no)
                    total_fetched += len(stockins)
                completed += 1
                if debug:
                    # 进度条显示
                    progress = completed / total_pages * 100
                    debug_print(f"\r[DEBUG] 进度: {completed}/{total_pages} ({progress:.1f}%) | 已获取: {total_fetched} 条 | 空页: {empty_pages}    ", end='', flush=True)
            
            if debug:
                print()
        
        if debug:
            if failed_pages:
                debug_print(f"[DEBUG] ⚠ {len(failed_pages)} 页请求失败")
                for p, err in failed_pages[:3]:
                    debug_print(f"  - 第{p}页: {err}")
            if empty_pages > 0:
                debug_print(f"[DEBUG] ⚠ {empty_pages} 页返回空数据（API可能有并发限制）")
        
        # 空页重试：对返回空数据的页面进行串行重试
        if empty_page_list:
            max_retry = 3
            retry_delay = 0.5
            
            if debug:
                debug_print(f"[DEBUG] 开始空页重试，共 {len(empty_page_list)} 页需要重试...")
            
            for retry_round in range(max_retry):
                if not empty_page_list:
                    break
                    
                still_empty = []
                recovered = 0
                
                for page_no in empty_page_list:
                    _time.sleep(retry_delay)
                    _, stockins, error = fetch_page(page_no)
                    
                    if not error and len(stockins) > 0:
                        all_stockins[page_no] = stockins
                        recovered += 1
                        if debug:
                            debug_print(f"\r[DEBUG] 重试第{retry_round+1}轮: 第{page_no}页恢复 {len(stockins)} 条", end='', flush=True)
                    else:
                        still_empty.append(page_no)
                
                if debug and recovered > 0:
                    print()
                    debug_print(f"[DEBUG] 重试第{retry_round+1}轮完成: 恢复 {recovered} 页，剩余 {len(still_empty)} 页为空")
                
                empty_page_list = still_empty
            
            if debug and empty_page_list:
                debug_print(f"[DEBUG] 重试后仍有 {len(empty_page_list)} 页为空: {sorted(empty_page_list)[:10]}...")
        
        # 记录空页日志
        log_empty_pages_func, log_data_mismatch_func = _get_logger_funcs()
        time_range = f"{start_time} ~ {end_time}"
        
        if log_empty_pages_func and empty_pages > 0:
            initial_empty = empty_pages
            recovered = initial_empty - len(empty_page_list) if empty_page_list else initial_empty
            log_empty_pages_func(
                api_name='stockin_refund',
                time_range=time_range,
                empty_pages=list(range(initial_empty)),
                retry_recovered=recovered,
                still_empty=empty_page_list
            )
        
        # 按页码顺序合并结果
        result_list = []
        for page_no in sorted(all_stockins.keys()):
            result_list.extend(all_stockins[page_no])
        
        # 检查总数是否匹配并记录日志
        if log_data_mismatch_func and len(result_list) != total_count:
            log_data_mismatch_func(
                api_name='stockin_refund',
                time_range=time_range,
                expected=total_count,
                actual=len(result_list),
                empty_pages=empty_page_list if empty_page_list else None,
                failed_pages=[p for p, _ in failed_pages] if failed_pages else None
            )
            # 加入重试队列
            add_task_func = _get_task_queue_func()
            if add_task_func:
                add_task_func('stockin_refund', start_time, end_time, total_count, len(result_list), 
                              shop_no=shop_no, warehouse_no=warehouse_no)
        
        if debug:
            debug_print(f"[DEBUG] 并行获取完成，共 {len(result_list)} 条")
            if len(result_list) != total_count:
                debug_print(f"[DEBUG] ⚠ 数据总数不匹配: 预期 {total_count}, 实际 {len(result_list)}")
        
        return result_list


# 退货入库单状态常量
class StockinRefundStatus:
    """退货入库单状态"""
    CANCELLED = 5           # 已取消
    WAIT_QC = 10            # 待质检
    QC_ING = 15             # 质检中
    WAIT_SIGN = 20          # 待签收
    WAIT_AUDIT = 50         # 待审核
    WAIT_STOCKIN = 60       # 待入库
    WAIT_PROCESS = 65       # 待处理
    STOCKIN_ING = 70        # 入库中
    WAIT_POST = 80          # 待过账
    COMPLETED = 110         # 已完成


# 时间类型常量
class StockinTimeType:
    """时间查询类型"""
    MODIFIED_TIME = 1       # 修改时间
    STOCKIN_TIME = 2        # 入库时间
    CREATED_TIME = 3        # 创建时间


# 保留别名兼容
StockinRefundAPI = StockinRefundQueryAPI


class StockinRefundQueryWithDetailAPI:
    
    METHOD = 'wdt.wms.stockin.refund.querywithdetail'
    
    def __init__(self, client: Optional[QimenClient] = None, 
                 config: Optional[WdtConfig] = None):
        self.client = client or QimenClient(config)
    
    def query(self, 
              start_time: str,
              end_time: str,
              time_type: int = 1,
              status: Optional[str] = None,
              warehouse_no: Optional[str] = None,
              shop_no: Optional[str] = None,
              stockin_no: Optional[str] = None,
              src_order_no: Optional[str] = None,
              refund_no: Optional[str] = None,
              logistics_no: Optional[str] = None,
              page_size: int = 50,
              page_no: int = 1,
              debug: bool = False) -> Dict:
        params = {
            'start_time': start_time,
            'end_time': end_time,
            'time_type': time_type
        }
        
        if status is not None:
            params['status'] = status
        if warehouse_no:
            params['warehouse_no'] = warehouse_no
        if shop_no:
            params['shop_no'] = shop_no
        if stockin_no:
            params['stockin_no'] = stockin_no
        if src_order_no:
            params['src_order_no'] = src_order_no
        if refund_no:
            params['refund_no'] = refund_no
        if logistics_no:
            params['logistics_no'] = logistics_no
        
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