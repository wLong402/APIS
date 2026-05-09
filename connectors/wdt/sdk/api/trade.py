#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
销售订单相关API
"""

import json
import time
import requests
from typing import Dict, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..client import QimenClient
from ..config import WdtConfig
from ..sign import WdtSignUtil

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


class RawTradeSearchAPI:
    """
    原始订单搜索API
    
    用于搜索销售原始订单数据
    API方法: wdt.sales.rawtrade.search
    
    响应数据结构:
        - status: 状态码，0表示成功
        - message: 错误信息
        - data.order: 订单列表
        - data.total_count: 总数量
    """
    
    METHOD = 'wdt.sales.rawtrade.search'
    
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
               tid: Optional[str] = None,
               shop_no: Optional[str] = None,
               is_slave: Optional[bool] = None,
               detail_mask: int = 1,
               page_size: int = 50,
               page_no: int = 1,
               debug: bool = False) -> Dict:
        """
        搜索原始订单
        
        Args:
            start_time: 修改起始时间，格式：YYYY-MM-DD HH:MM:SS（必填）
            end_time: 修改结束时间，格式：YYYY-MM-DD HH:MM:SS（必填）
            time_type: 时间类型，1=修改时间（默认1）
            tid: 原始单号
            shop_no: 店铺编号（不支持批量查询）
            is_slave: 是否使用从库查询（仅对开通从库配置客户生效）
            detail_mask: 优惠明细掩码，1=返回优惠明细，0=不返回（默认1）
            page_size: 分页大小（单量较大建议200以下）
            page_no: 页号，从0开始（注意：不是从1开始！）
            
        Returns:
            查询结果:
                - status: 状态码，0表示成功
                - message: 错误信息（无错误时不返回）
                - data.order: 订单列表
                - data.total_count: 总数量
                
        订单字段说明（order）:
            - rec_id: 唯一键
            - tid: 原始单号
            - shop_no: 店铺编号
            - process_status: 系统状态（10待递交/20已递交/30部分发货/40已发货/60已完成/70已取消）
            - trade_status: 平台状态（30待发货/40部分发货/50已发货/70已完成等）
            - pay_status: 支付状态（0未付款/1部分付款/2已付款）
            - refund_status: 退款状态（0无退款/1申请退款/2部分退款/3全部退款）
            - trade_time: 下单时间
            - pay_time: 支付时间
            - buyer_nick: 客户网名
            - receiver_name: 收件人姓名
            - receiver_mobile: 收件人手机
            - receiver_address: 收件人地址
            - goods_amount: 货款
            - post_amount: 邮费
            - receivable: 应收
            - received: 已收
            - trade_orders: 原始单明细列表
            - discount_list: 优惠明细列表（需设置detail_mask=1）
        """
        # 必填参数（参考退款单API）
        params = {
            'start_time': start_time,
            'end_time': end_time,
            'time_type': time_type
        }
        
        # 添加可选参数
        if tid:
            params['tid'] = tid
        if shop_no:
            params['shop_no'] = shop_no
        if is_slave is not None:
            params['is_slave'] = is_slave
        if detail_mask:
            params['detail_mask'] = detail_mask
        
        pager = {
            'page_size': page_size,
            'page_no': page_no
        }
        
        return self.client.call(self.METHOD, params, pager, debug=debug)
    
    def search_by_tid(self, tid: str) -> Dict:
        """
        根据原始单号查询订单
        
        Args:
            tid: 原始单号
            
        Returns:
            查询结果
        """
        return self.search(tid=tid)
    
    def search_by_time_range(self,
                             start_time: str,
                             end_time: str,
                             shop_no: Optional[str] = None,
                             with_discount: bool = True,
                             page_size: int = 50,
                             page_no: int = 1) -> Dict:
        """
        按时间范围查询订单
        
        Args:
            start_time: 修改起始时间
            end_time: 修改结束时间
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
            shop_no=shop_no,
            detail_mask=1 if with_discount else 0,
            page_size=page_size,
            page_no=page_no
        )
    
    def search_all(self,
                   start_time: str,
                   end_time: str,
                   time_type: int = 3,
                   shop_no: Optional[str] = None,
                   with_discount: bool = True,
                   page_size: int = 50,
                   debug: bool = False,
                   max_workers: int = 10) -> List[Dict]:
        """
        搜索所有原始订单（并行分页）
        
        Args:
            start_time: 修改起始时间
            end_time: 修改结束时间
            time_type: 时间类型，1=修改时间（默认1）
            shop_no: 店铺编号（可选）
            with_discount: 是否返回优惠明细
            page_size: 每页数量（建议200以下）
            debug: 是否打印调试信息
            max_workers: 并行线程数（默认10）
            
        Returns:
            所有订单列表
        """
        # 第一步：获取第一页，仅用于确定总数
        debug_print = _get_debug_print()
        if debug:
            debug_print(f"    [DEBUG] 请求第 1 页（仅获取总数）...")
            debug_print(f"    [DEBUG] 参数: start_time={start_time}, end_time={end_time}, page_size={page_size}")
        
        import time as _time
        _start = _time.time()
        
        first_result = self.search(
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            shop_no=shop_no,
            detail_mask=1 if with_discount else 0,
            page_size=page_size,
            page_no=1,
            debug=debug  # 传递debug参数
        )
        
        if debug:
            debug_print(f"    [DEBUG] 响应耗时: {_time.time() - _start:.2f}秒")
        
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
        
        # 第二步：从最后一页往前并行获取（避免新数据插入导致分页偏移）
        # 第1页最后重新获取，确保拿到最新数据
        all_orders = {}  # 用字典保存，key是页码
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
                    orders = result.get('data', {}).get('order', [])
                    return page_no, orders, None
                return page_no, [], f"status={result.get('status')}, msg={result.get('message')}"
            except Exception as e:
                return page_no, [], str(e)
        
        empty_page_list = []  # 记录返回空数据的页码
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 从最后一页往前提交请求（total_pages, total_pages-1, ..., 2, 1）
            # 倒序提交可以让后面的页先完成，减少分页偏移影响
            page_order = list(range(total_pages, 0, -1))  # [total_pages, ..., 2, 1]
            futures = {executor.submit(fetch_page, p): p for p in page_order}
            
            completed = 0
            total_fetched = 0
            empty_pages = 0  # 记录返回空数据的页数
            
            for future in as_completed(futures):
                page_no, orders, error = future.result()
                if error:
                    failed_pages.append((page_no, error))
                else:
                    all_orders[page_no] = orders
                    if len(orders) == 0:
                        empty_pages += 1
                        empty_page_list.append(page_no)
                    total_fetched += len(orders)
                completed += 1
                if debug:
                    # 进度条显示（从后往前）
                    progress = completed / total_pages * 100
                    debug_print(f"\r    [DEBUG] 进度: {completed}/{total_pages} ({progress:.1f}%) | 已获取: {total_fetched} 条 | 空页: {empty_pages}    ", end='', flush=True)
            
            if debug:
                print()  # 换行
        
        if debug:
            if failed_pages:
                debug_print(f"    [DEBUG] ⚠ {len(failed_pages)} 页请求失败")
                # 显示前3个失败原因
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
                    _, orders, error = fetch_page(page_no)
                    
                    if not error and len(orders) > 0:
                        all_orders[page_no] = orders
                        recovered += 1
                        if debug:
                            debug_print(f"\r    [DEBUG] 重试第{retry_round+1}轮: 第{page_no}页恢复 {len(orders)} 条", end='', flush=True)
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
        
        if log_empty_pages_func and (initial_empty_count := len([p for p in range(2, total_pages + 1) if p in empty_page_list or any(p == ep for ep in empty_page_list)]) if empty_page_list else 0) > 0:
            # 计算初始空页数和恢复数
            initial_empty = empty_pages  # 并行获取时的空页数
            recovered = initial_empty - len(empty_page_list) if empty_page_list else initial_empty
            if initial_empty > 0:
                log_empty_pages_func(
                    api_name='raw_trade',
                    time_range=time_range,
                    empty_pages=list(range(initial_empty)),  # 占位
                    retry_recovered=recovered,
                    still_empty=empty_page_list
                )
        
        # 按页码顺序合并结果
        result_list = []
        for page_no in sorted(all_orders.keys()):
            result_list.extend(all_orders[page_no])
        
        # 检查总数是否匹配并记录日志
        if log_data_mismatch_func and len(result_list) != total_count:
            log_data_mismatch_func(
                api_name='raw_trade',
                time_range=time_range,
                expected=total_count,
                actual=len(result_list),
                empty_pages=empty_page_list if empty_page_list else None,
                failed_pages=[p for p, _ in failed_pages] if failed_pages else None
            )
            # 加入重试队列
            add_task_func = _get_task_queue_func()
            if add_task_func:
                add_task_func('trade', start_time, end_time, total_count, len(result_list), shop_no=shop_no)
        
        if debug:
            debug_print(f"    [DEBUG] 并行获取完成，共 {len(result_list)} 条")
            if len(result_list) != total_count:
                debug_print(f"    [DEBUG] ⚠ 数据总数不匹配: 预期 {total_count}, 实际 {len(result_list)}")
        
        return result_list


# 订单状态常量
class TradeStatus:
    """平台订单状态"""
    UNCONFIRMED = 10      # 未确认
    WAIT_PAYMENT = 20     # 待尾款
    WAIT_DELIVERY = 30    # 待发货
    PARTIAL_DELIVERED = 40  # 部分发货
    DELIVERED = 50        # 已发货
    SIGNED = 60           # 已签收
    COMPLETED = 70        # 已完成
    REFUNDED = 80         # 已退款
    CLOSED = 90           # 已关闭


class ProcessStatus:
    """系统处理状态"""
    WAIT_SUBMIT = 10           # 待递交
    PARTIAL_WAIT_SUBMIT = 15   # 部分发货待递交
    SUBMITTED = 20             # 已递交
    PARTIAL_DELIVERED = 30     # 部分发货
    DELIVERED = 40             # 已发货
    COMPLETED = 60             # 已完成
    CANCELLED = 70             # 已取消


class PayStatus:
    """支付状态"""
    UNPAID = 0       # 未付款
    PARTIAL_PAID = 1  # 部分付款
    PAID = 2          # 已付款


class RefundStatus:
    """退款状态"""
    NO_REFUND = 0         # 无退款
    APPLY_REFUND = 1      # 申请退款
    PARTIAL_REFUND = 2    # 部分退款
    FULL_REFUND = 3       # 全部退款


class TradeQueryAPI:
    """
    订单查询API（带明细）
    
    用于查询ERP系统订单数据
    API方法: wdt.sales.tradequery.querywithdetail
    
    响应数据结构:
        - status: 状态码，0表示成功
        - message: 错误信息
        - data.order: 订单列表
        - data.total_count: 总数量
    """
    
    METHOD = 'wdt.sales.tradequery.querywithdetail'
    
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
              trade_no: Optional[str] = None,
              src_tid: Optional[str] = None,
              shop_no: Optional[str] = None,
              warehouse_no: Optional[str] = None,
              status: Optional[str] = None,
              logistics_no: Optional[str] = None,
              trade_from: Optional[str] = None,
              order_type: int = 0,
              time_type: int = 1,
              is_slave: Optional[bool] = None,
              cal_share_post_amount: bool = False,
              need_gift_relation: int = 1,
              accurate_query: int = 0,
              cut_logistics_no: int = 0,
              page_size: int = 50,
              page_no: int = 1) -> Dict:
        """
        查询订单（带明细）- 根据文档修正
        
        API方法: wdt.sales.tradequery.querywithdetail
        
        Args:
            start_time: 修改起始时间，格式：YYYY-MM-DD HH:MM:SS（必填）
            end_time: 修改结束时间，格式：YYYY-MM-DD HH:MM:SS（必填）
            trade_no: 订单编号（旺店通系统订单号）
            src_tid: 原始单号（平台订单号），多个用逗号分隔
            shop_no: 店铺编号（暂不支持批量查询）
            warehouse_no: 仓库编号
            status: 订单状态，多个用逗号分隔
            logistics_no: 物流单号
            trade_from: 订单来源（1=API抓单/2=手工建单/3=导入等）
            order_type: 排序类型（0=默认排序/1=修改时间降序，默认0）
            time_type: 时间类型（1=修改时间/2=付款时间/3=下单时间，默认1）
            is_slave: 是否使用从库查询
            cal_share_post_amount: 是否计算分摊邮费（默认False）
            need_gift_relation: 是否返回赠品关联关系（0=不返回/1=返回，默认1）
            accurate_query: 是否强制指定src_tid精准查询（0=否/1=是，默认0）
            cut_logistics_no: 是否截取物流单号（0=不截取/1=截取，默认0）
            page_size: 分页大小（建议200以下）
            page_no: 页号，从0开始！
            
        Returns:
            查询结果:
                - status: 状态码，0表示成功
                - data.order: 订单列表
                - data.total_count: 总数量
        """
        # 必填参数
        params = {
            'start_time': start_time,
            'end_time': end_time
        }
        
        # 添加可选参数（根据文档）
        if trade_no:
            params['trade_no'] = trade_no
        if src_tid:
            params['src_tid'] = src_tid
        if shop_no:
            params['shop_no'] = shop_no
        if warehouse_no:
            params['warehouse_no'] = warehouse_no
        if status:
            params['status'] = status
        if logistics_no:
            params['logistics_no'] = logistics_no
        if trade_from:
            params['trade_from'] = trade_from
        if order_type != 0:
            params['order_type'] = order_type
        if time_type != 1:
            params['time_type'] = time_type
        if is_slave is not None:
            params['is_slave'] = is_slave
        if cal_share_post_amount:
            params['cal_share_post_amount'] = cal_share_post_amount
        if need_gift_relation != 1:
            params['need_gift_relation'] = need_gift_relation
        if accurate_query != 0:
            params['accurate_query'] = accurate_query
        if cut_logistics_no != 0:
            params['cut_logistics_no'] = cut_logistics_no
        
        pager = {
            'page_size': page_size,
            'page_no': page_no  # 从0开始！
        }
        
        return self.client.call(self.METHOD, params, pager)
    
    def query_by_trade_no(self, trade_no: str) -> Dict:
        """
        根据订单编号查询
        
        Args:
            trade_no: 订单编号（旺店通系统订单号）
            
        Returns:
            查询结果
        """
        return self.query(trade_no=trade_no)
    
    def query_by_src_tid(self, src_tid: str, accurate: bool = True) -> Dict:
        """
        根据原始单号查询
        
        Args:
            src_tid: 原始单号（平台订单号），多个用逗号分隔
            accurate: 是否精准查询
            
        Returns:
            查询结果
        """
        return self.query(src_tid=src_tid, accurate_query=accurate)
    
    def query_by_logistics_no(self, logistics_no: str) -> Dict:
        """
        根据物流单号查询
        
        Args:
            logistics_no: 物流单号
            
        Returns:
            查询结果
        """
        return self.query(logistics_no=logistics_no)
    
    def query_by_status(self,
                        start_time: str,
                        end_time: str,
                        status: str,
                        shop_no: Optional[str] = None,
                        page_size: int = 50,
                        page_no: int = 1) -> Dict:
        """
        按状态查询订单
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            status: 订单状态，多个用逗号分隔
            shop_no: 店铺编号（可选）
            page_size: 分页大小
            page_no: 页号
            
        Returns:
            查询结果
        """
        return self.query(
            start_time=start_time,
            end_time=end_time,
            status=status,
            shop_no=shop_no,
            page_size=page_size,
            page_no=page_no
        )
    
    def query_all(self,
                  start_time: str,
                  end_time: str,
                  shop_no: Optional[str] = None,
                  time_type: int = 1,
                  page_size: int = 50,
                  debug: bool = False,
                  max_workers: int = 10) -> List[Dict]:
        """
        查询所有订单（并行分页）- 根据文档修正
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            shop_no: 店铺编号（可选）
            time_type: 时间类型（1=修改时间/2=付款时间/3=下单时间，默认1）
            page_size: 每页数量（建议200以下）
            debug: 是否打印调试信息
            max_workers: 并行线程数（默认10）
            
        Returns:
            所有订单列表
        """
        debug_print = _get_debug_print()
        # 第一步：获取第1页，仅用于确定总数
        if debug:
            debug_print(f"    [DEBUG] 请求第 1 页（仅获取总数）...")
        
        first_result = self.query(
            start_time=start_time,
            end_time=end_time,
            shop_no=shop_no,
            time_type=time_type,
            page_size=page_size,
            page_no=1
        )
        
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
        all_orders = {}
        failed_pages = []
        
        def fetch_page(page_no):
            try:
                result = self.query(
                    start_time=start_time,
                    end_time=end_time,
                    shop_no=shop_no,
                    time_type=time_type,
                    page_size=page_size,
                    page_no=page_no
                )
                if str(result.get('status')) == '0':
                    orders = result.get('data', {}).get('order', [])
                    return page_no, orders, None
                return page_no, [], f"status={result.get('status')}, msg={result.get('message')}"
            except Exception as e:
                return page_no, [], str(e)
        
        import time as _time
        empty_page_list = []  # 记录返回空数据的页码
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 从最后一页往前提交请求（total_pages, ..., 2, 1）
            page_order = list(range(total_pages, 0, -1))
            futures = {executor.submit(fetch_page, p): p for p in page_order}
            
            completed = 0
            total_fetched = 0
            empty_pages = 0
            
            for future in as_completed(futures):
                page_no, orders, error = future.result()
                if error:
                    failed_pages.append((page_no, error))
                else:
                    all_orders[page_no] = orders
                    if len(orders) == 0:
                        empty_pages += 1
                        empty_page_list.append(page_no)
                    total_fetched += len(orders)
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
                    _, orders, error = fetch_page(page_no)
                    
                    if not error and len(orders) > 0:
                        all_orders[page_no] = orders
                        recovered += 1
                        if debug:
                            debug_print(f"\r    [DEBUG] 重试第{retry_round+1}轮: 第{page_no}页恢复 {len(orders)} 条", end='', flush=True)
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
                api_name='erp_trade',
                time_range=time_range,
                empty_pages=list(range(initial_empty)),
                retry_recovered=recovered,
                still_empty=empty_page_list
            )
        
        # 按页码顺序合并结果
        result_list = []
        for page_no in sorted(all_orders.keys()):
            result_list.extend(all_orders[page_no])
        
        # 检查总数是否匹配并记录日志
        if log_data_mismatch_func and len(result_list) != total_count:
            log_data_mismatch_func(
                api_name='erp_trade',
                time_range=time_range,
                expected=total_count,
                actual=len(result_list),
                empty_pages=empty_page_list if empty_page_list else None,
                failed_pages=[p for p, _ in failed_pages] if failed_pages else None
            )
            # 加入重试队列
            add_task_func = _get_task_queue_func()
            if add_task_func:
                add_task_func('erp', start_time, end_time, total_count, len(result_list), shop_no=shop_no)
        
        if debug:
            debug_print(f"    [DEBUG] 并行获取完成，共 {len(result_list)} 条")
            if len(result_list) != total_count:
                debug_print(f"    [DEBUG] ⚠ 数据总数不匹配: 预期 {total_count}, 实际 {len(result_list)}")
        
        return result_list


# ERP订单状态常量
class ERPTradeStatus:
    """ERP订单状态"""
    OFFLINE_REFUND = 4        # 线下退款
    CANCELLED = 5             # 已取消
    WAIT_TO_PREORDER = 6      # 待转预订单(待审核)
    WAIT_TO_COMPLETE = 7      # 待转已完成
    UNPAID = 10               # 未付款
    WAIT_FINAL_PAYMENT = 12   # 待尾款
    WAIT_UNPAID = 15          # 等未付
    DELAY_AUDIT = 16          # 延时审核
    PREORDER_PREPROCESSING = 19  # 预订单前处理
    AUDIT_PREPROCESSING = 20  # 审核前处理
    AUTO_WAIT_DELIVERY = 21   # 自流转待发货
    ABNORMAL = 23             # 异常订单
    EXCHANGE_PREORDER = 24    # 换货预订单
    WAIT_PROCESS_PREORDER = 25  # 待处理预订单
    WAIT_ASSIGN_PREORDER = 27   # 待分配预订单
    WAIT_CS_AUDIT = 30        # 待客审
    WAIT_FINANCE_AUDIT = 35   # 待财审
    AUDITING = 40             # 审核中
    AUDITED = 55              # 已审核
    SHIPPED = 95              # 已发货
    COST_CONFIRM = 96         # 成本确认
    POSTED = 101              # 已过账
    COMPLETED = 110           # 已完成


# 订单类型常量
class TradeType:
    """订单类型"""
    ONLINE_SALE = 1           # 网店销售
    OFFLINE_ORDER = 2         # 线下订单
    AFTER_SALE_EXCHANGE = 3   # 售后换货
    WHOLESALE = 4             # 批发业务
    CASH_SALE = 7             # 现款销售
    DISTRIBUTION = 8          # 分销订单
    CUSTOM_TYPE_1 = 101       # 自定义类型一
    CUSTOM_TYPE_2 = 102       # 自定义类型二
    CUSTOM_TYPE_3 = 103       # 自定义类型三
    CUSTOM_TYPE_4 = 104       # 自定义类型四
    CUSTOM_TYPE_5 = 105       # 自定义类型五


# 订单来源常量
class TradeFrom:
    """订单来源"""
    API = 1                   # API抓单
    MANUAL = 2                # 手工建单
    IMPORT = 3                # 导入
    COPY = 4                  # 复制订单
    PUSH = 5                  # 接口推送
    REISSUE = 6               # 补发订单
    PDA = 7                   # PDA选货开单
    DISTRIBUTION_REISSUE = 8  # 分销补发订单


# 时间类型常量
class TradeTimeType:
    """时间查询类型"""
    MODIFIED_TIME = 1         # 修改时间
    PAY_TIME = 2              # 付款时间
    TRADE_TIME = 3            # 下单时间


class HistoryTradeQueryAPI:
    METHOD = 'wdt.sales.tradequery.queryhistorywithdetail'
    
    def __init__(self, client: Optional[QimenClient] = None, config: Optional[WdtConfig] = None):
        self.client = client or QimenClient(config)
    
    def query(self,
              start_time: str,
              end_time: str,
              trade_no: Optional[str] = None,
              src_tid: Optional[str] = None,
              shop_no: Optional[str] = None,
              warehouse_no: Optional[str] = None,
              status: Optional[str] = None,
              logistics_no: Optional[str] = None,
              time_type: int = 1,
              is_slave: Optional[bool] = None,
              cal_share_post_amount: bool = False,
              accurate_query: int = 0,
              page_size: int = 50,
              page_no: int = 1,
              debug: bool = False) -> Dict:
        params = {'start_time': start_time, 'end_time': end_time}
        if trade_no:
            params['trade_no'] = trade_no
        if src_tid:
            params['src_tid'] = src_tid
        if shop_no:
            params['shop_no'] = shop_no
        if warehouse_no:
            params['warehouse_no'] = warehouse_no
        if status:
            params['status'] = status
        if logistics_no:
            params['logistics_no'] = logistics_no
        if time_type != 1:
            params['time_type'] = time_type
        if is_slave is not None:
            params['is_slave'] = is_slave
        if cal_share_post_amount:
            params['cal_share_post_amount'] = cal_share_post_amount
        if accurate_query != 0:
            params['accurate_query'] = accurate_query
        
        pager = {'page_size': page_size, 'page_no': page_no}
        return self.client.call(self.METHOD, params, pager, debug=debug)
    
    def query_all(self,
                  start_time: str,
                  end_time: str,
                  shop_no: Optional[str] = None,
                  time_type: int = 1,
                  page_size: int = 50,
                  debug: bool = False,
                  max_workers: int = 10) -> List[Dict]:
        debug_print = _get_debug_print()
        
        first_result = self.query(
            start_time=start_time, end_time=end_time, shop_no=shop_no,
            time_type=time_type, page_size=page_size, page_no=1, debug=debug
        )
        
        if str(first_result.get('status')) != '0':
            if debug:
                debug_print(f"    [DEBUG] API返回错误: {first_result.get('message')}")
            return []
        
        data = first_result.get('data', {})
        total_count = int(data.get('total_count', 0))
        first_orders = data.get('order', [])
        
        if debug:
            debug_print(f"    [DEBUG] 总数: {total_count}")
        
        if total_count == 0:
            return []
        
        total_pages = (total_count + page_size - 1) // page_size
        if total_pages == 1:
            return first_orders
        
        all_orders = {1: first_orders}
        
        def fetch_page(page_no):
            try:
                result = self.query(start_time=start_time, end_time=end_time, shop_no=shop_no,
                                    time_type=time_type, page_size=page_size, page_no=page_no)
                if str(result.get('status')) == '0':
                    return page_no, result.get('data', {}).get('order', []), None
                return page_no, [], result.get('message')
            except Exception as e:
                return page_no, [], str(e)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_page, p): p for p in range(2, total_pages + 1)}
            for future in as_completed(futures):
                page_no, orders, error = future.result()
                if not error:
                    all_orders[page_no] = orders
                if debug:
                    debug_print(f"\r    [DEBUG] 进度: {len(all_orders)}/{total_pages}", end='', flush=True)
            if debug:
                print()
        
        result = []
        for p in sorted(all_orders.keys()):
            result.extend(all_orders[p])
        return result
    
    def query_time_range(self,
                         start_time: str,
                         end_time: str,
                         shop_no: Optional[str] = None,
                         time_type: int = 1,
                         page_size: int = 50,
                         debug: bool = False,
                         max_workers: int = 5) -> List[Dict]:
        debug_print = _get_debug_print()
        from datetime import datetime, timedelta
        
        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        
        intervals = []
        current = start_dt
        while current < end_dt:
            interval_end = min(current + timedelta(minutes=60), end_dt)
            intervals.append((current.strftime('%Y-%m-%d %H:%M:%S'), interval_end.strftime('%Y-%m-%d %H:%M:%S')))
            current = interval_end
        
        if debug:
            debug_print(f"    [DEBUG] 分割为 {len(intervals)} 个60分钟区间")
        
        all_orders = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.query_all, s, e, shop_no, time_type, page_size, debug): (s, e) for s, e in intervals}
            completed = 0
            for future in as_completed(futures):
                try:
                    orders = future.result()
                    all_orders.extend(orders)
                except Exception as e:
                    if debug:
                        debug_print(f"    [DEBUG] 区间查询失败: {e}")
                completed += 1
                if debug:
                    debug_print(f"\r    [DEBUG] 进度: {completed}/{len(intervals)} | 已获取: {len(all_orders)} 条", end='', flush=True)
            if debug:
                print()
        
        if debug:
            debug_print(f"    [DEBUG] 查询完成，共 {len(all_orders)} 条")
        return all_orders
