#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
出库单相关API
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


class StockoutSalesQueryAPI:
    """
    销售出库单查询API（带明细）
    
    用于查询ERP销售出库单信息
    API方法: wdt.wms.stockout.sales.querywithdetail
    
    注意事项:
        - 时间跨度限制：start_time 和 end_time 最大跨度为 60 分钟
        - 分页：page_no 从 0 开始
        - 权限校验：店铺、仓库权限
        - 淘系、拼多多及系统供销平台订单不返回用户隐私数据
    
    响应数据结构:
        - status: 状态码，0表示成功
        - message: 错误信息
        - data.order: 出库单列表
        - data.total_count: 总数量
    """
    
    # API方法名
    METHOD = 'wdt.wms.stockout.sales.querywithdetail'
    
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
              status_type: int = 0,
              status: Optional[str] = None,
              warehouse_no: Optional[str] = None,
              shop_nos: Optional[str] = None,
              stockout_no: Optional[str] = None,
              src_order_no: Optional[str] = None,
              logistics_no: Optional[str] = None,
              page_size: int = 50,
              page_no: int = 1,
              debug: bool = False) -> Dict:
        """
        查询销售出库单
        
        Args:
            start_time: 开始时间，格式：YYYY-MM-DD HH:MM:SS
            end_time: 结束时间，格式：YYYY-MM-DD HH:MM:SS（与start_time最大跨度60分钟）
            status_type: 出库单状态类型（必填，默认0）
                - 0: 延时发货&已完成（按发货时间查询）
                - 1: 已取消
                - 2: 待分配~延时发货（此条件会返回延时发货状态的订单）
                - 3: 按照指定的status状态字段查询（按修改时间查询）
            status: 出库单状态详细（status_type=3时使用，多个状态用逗号分隔）
                - 5: 已取消
                - 10: 待放回(拣货待放回)
                - 50: 待审核
                - 51: 缺货
                - 52: 缺货待入库
                - 53: WMS已接单
                - 54: 获取电子面单
                - 58: 档口锁定
                - 60: 待分配
                - 61: 排队中
                - 63: 待补货
                - 65: 待处理
                - 70: 待发货
                - 73: 爆款锁定
                - 74: 预打包
                - 75: 待拣货
                - 77: 拣货中
                - 79: 已拣货
                - 90: 延时发货
                - 110: 已完成
                - -1: 未发货
            warehouse_no: 仓库编号（可选）
            shop_nos: 多个店铺编号，逗号分隔（可选）
            stockout_no: 出库单号（传入可不传时间条件）
            src_order_no: 系统订单号（传入可不传时间条件）
            logistics_no: 物流单号（传入可不传时间条件）
            page_size: 每页数量（默认50，建议200以下）
            page_no: 页码（从1开始）
            debug: 是否打印调试信息
            
        Returns:
            查询结果，包含：
                - status: 状态码，0表示成功
                - data.order: 出库单列表
                - data.total_count: 总数量
        """
        params = {
            'start_time': start_time,
            'end_time': end_time,
            'status_type': status_type
        }
        
        if status is not None:
            params['status'] = status
        if warehouse_no:
            params['warehouse_no'] = warehouse_no
        if shop_nos:
            params['shop_nos'] = shop_nos
        if stockout_no:
            params['stockout_no'] = stockout_no
        if src_order_no:
            params['src_order_no'] = src_order_no
        if logistics_no:
            params['logistics_no'] = logistics_no
        
        pager = {
            'page_size': page_size,
            'page_no': page_no
        }
        
        result = self.client.call(self.METHOD, params, pager)
        
        if debug:
            debug_print = _get_debug_print()
            status_code = result.get('status')
            data = result.get('data', {})
            total = data.get('total_count', 0)
            orders = data.get('order', [])
            debug_print(f"    [DEBUG] API响应: status={status_code}, total_count={total}, 本页={len(orders)}条")
        
        return result
    
    def query_all(self,
                  start_time: str,
                  end_time: str,
                  status_type: int = 0,
                  status: Optional[str] = None,
                  warehouse_no: Optional[str] = None,
                  shop_nos: Optional[str] = None,
                  page_size: int = 50,
                  debug: bool = False,
                  max_workers: int = 10) -> List[Dict]:
        """
        查询所有销售出库单（并行分页）
        
        注意：由于API时间跨度限制为60分钟，建议使用 --by-hours 参数按小时拉取
        
        Args:
            start_time: 开始时间
            end_time: 结束时间（与start_time最大跨度60分钟）
            status_type: 出库单状态类型（默认0=延时发货&已完成）
            status: 出库单状态详细（status_type=3时使用）
            warehouse_no: 仓库编号（可选）
            shop_nos: 店铺编号（可选）
            page_size: 每页数量（建议200以下）
            debug: 是否打印调试信息
            max_workers: 并行线程数（默认10）
            
        Returns:
            所有出库单列表
        """
        debug_print = _get_debug_print()
        # 第一步：获取第一页，仅用于确定总数
        if debug:
            debug_print(f"    [DEBUG] 请求第 1 页（仅获取总数）...")
            debug_print(f"    [DEBUG] 参数: start_time={start_time}, end_time={end_time}, status_type={status_type}")
        
        import time as _time
        _start = _time.time()
        
        first_result = self.query(
            start_time=start_time,
            end_time=end_time,
            status_type=status_type,
            status=status,
            warehouse_no=warehouse_no,
            shop_nos=shop_nos,
            page_size=page_size,
            page_no=1,
            debug=debug
        )
        
        if debug:
            debug_print(f"    [DEBUG] 响应耗时: {_time.time() - _start:.2f}秒")
        
        status_code = first_result.get('status')
        if str(status_code) != '0':
            if debug:
                debug_print(f"    [DEBUG] API返回错误: status={status_code}, message={first_result.get('message')}")
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
        all_stockouts = {}
        failed_pages = []
        
        def fetch_page(page_no):
            try:
                result = self.query(
                    start_time=start_time,
                    end_time=end_time,
                    status_type=status_type,
                    status=status,
                    warehouse_no=warehouse_no,
                    shop_nos=shop_nos,
                    page_size=page_size,
                    page_no=page_no
                )
                if str(result.get('status')) == '0':
                    stockouts = result.get('data', {}).get('order', [])
                    return page_no, stockouts, None
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
                page_no, stockouts, error = future.result()
                if error:
                    failed_pages.append((page_no, error))
                else:
                    all_stockouts[page_no] = stockouts
                    if len(stockouts) == 0:
                        empty_pages += 1
                        empty_page_list.append(page_no)
                    total_fetched += len(stockouts)
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
            max_retry = 3
            retry_delay = 0.5
            
            if debug:
                debug_print(f"    [DEBUG] 开始空页重试，共 {len(empty_page_list)} 页需要重试...")
            
            for retry_round in range(max_retry):
                if not empty_page_list:
                    break
                    
                still_empty = []
                recovered = 0
                
                for page_no in empty_page_list:
                    _time.sleep(retry_delay)
                    _, stockouts, error = fetch_page(page_no)
                    
                    if not error and len(stockouts) > 0:
                        all_stockouts[page_no] = stockouts
                        recovered += 1
                        if debug:
                            debug_print(f"\r    [DEBUG] 重试第{retry_round+1}轮: 第{page_no}页恢复 {len(stockouts)} 条", end='', flush=True)
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
                api_name='stockout_sales',
                time_range=time_range,
                empty_pages=list(range(initial_empty)),
                retry_recovered=recovered,
                still_empty=empty_page_list
            )
        
        # 按页码顺序合并结果
        result_list = []
        for page_no in sorted(all_stockouts.keys()):
            result_list.extend(all_stockouts[page_no])
        
        # 检查总数是否匹配并记录日志
        if log_data_mismatch_func and len(result_list) != total_count:
            log_data_mismatch_func(
                api_name='stockout_sales',
                time_range=time_range,
                expected=total_count,
                actual=len(result_list),
                empty_pages=empty_page_list if empty_page_list else None,
                failed_pages=[p for p, _ in failed_pages] if failed_pages else None
            )
            # 加入重试队列
            add_task_func = _get_task_queue_func()
            if add_task_func:
                add_task_func('stockout', start_time, end_time, total_count, len(result_list), 
                              shop_no=shop_nos, warehouse_no=warehouse_no)
        
        if debug:
            debug_print(f"    [DEBUG] 并行获取完成，共 {len(result_list)} 条")
            if len(result_list) != total_count:
                debug_print(f"    [DEBUG] ⚠ 数据总数不匹配: 预期 {total_count}, 实际 {len(result_list)}")
        
        return result_list


# 出库单状态类型常量
class StockoutStatusType:
    """出库单状态类型（status_type参数）"""
    DELAYED_AND_COMPLETED = 0   # 延时发货&已完成（按发货时间查询）
    CANCELLED = 1               # 已取消
    WAIT_TO_DELAYED = 2         # 待分配~延时发货
    BY_STATUS = 3               # 按照指定的status状态字段查询（按修改时间查询）


# 出库单状态常量
class StockoutStatus:
    """出库单状态（status参数）"""
    CANCELLED = 5               # 已取消
    WAIT_RETURN = 10            # 待放回(拣货待放回)
    WAIT_AUDIT = 50             # 待审核
    OUT_OF_STOCK = 51           # 缺货
    OUT_OF_STOCK_WAIT = 52      # 缺货待入库
    WMS_RECEIVED = 53           # WMS已接单
    GET_WAYBILL = 54            # 获取电子面单
    STALL_LOCKED = 58           # 档口锁定
    WAIT_ASSIGN = 60            # 待分配
    QUEUING = 61                # 排队中
    WAIT_REPLENISH = 63         # 待补货
    WAIT_PROCESS = 65           # 待处理
    WAIT_SHIP = 70              # 待发货
    HOT_LOCKED = 73             # 爆款锁定
    PRE_PACK = 74               # 预打包
    WAIT_PICK = 75              # 待拣货
    PICKING = 77                # 拣货中
    PICKED = 79                 # 已拣货
    DELAYED = 90                # 延时发货
    COMPLETED = 110             # 已完成
    NOT_SHIPPED = -1            # 未发货


# 保留旧类名兼容
StockoutSalesAPI = StockoutSalesQueryAPI


class StockoutOtherAPI:
    """
    其他出库单API
    
    用于查询非销售类型的出库单
    """
    
    METHOD = 'wdt.wms.stockout.other.querywithdetail'
    
    def __init__(self, client: Optional[QimenClient] = None,
                 config: Optional[WdtConfig] = None):
        self.client = client or QimenClient(config)
    
    def query(self,
              start_time: str,
              end_time: str,
              page_size: int = 20,
              page_no: int = 1) -> Dict:
        """
        查询其他出库单
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            page_size: 每页数量
            page_no: 页码（从1开始）
            
        Returns:
            查询结果
        """
        params = {
            'start_time': start_time,
            'end_time': end_time
        }
        
        pager = {
            'page_size': page_size,
            'page_no': page_no
        }
        
        return self.client.call(self.METHOD, params, pager)


class StockoutSalesQueryWithDetailAPI:
    """
    销售出库单查询API（带明细）
    
    用于查询ERP销售出库单信息
    API方法: wms.stockout.Sales.queryWithDetail
    """
    
    # METHOD = 'wms.stockout.Sales.queryWithDetail'  # 原始（无效）
    METHOD = 'wdt.wms.stockout.sales.querywithdetail'
    
    def __init__(self, client: Optional[QimenClient] = None, 
                 config: Optional[WdtConfig] = None):
        self.client = client or QimenClient(config)
    
    def query(self, 
              start_time: str,
              end_time: str,
              status_type: int = 0,
              status: Optional[str] = None,
              warehouse_no: Optional[str] = None,
              shop_nos: Optional[str] = None,
              stockout_no: Optional[str] = None,
              src_order_no: Optional[str] = None,
              logistics_no: Optional[str] = None,
              page_size: int = 50,
              page_no: int = 1,
              debug: bool = False) -> Dict:
        params = {
            'start_time': start_time,
            'end_time': end_time,
            'status_type': status_type
        }
        
        if status is not None:
            params['status'] = status
        if warehouse_no:
            params['warehouse_no'] = warehouse_no
        if shop_nos:
            params['shop_nos'] = shop_nos
        if stockout_no:
            params['stockout_no'] = stockout_no
        if src_order_no:
            params['src_order_no'] = src_order_no
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
