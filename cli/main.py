# -*- coding: utf-8 -*-
"""
CLI 主入口

使用 argparse 实现命令行接口
"""

import argparse
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

from core.config import get_config, DatabaseConfig
from core.database import reset_db_manager
from core.logger import get_logger, debug_print

logger = get_logger('cli')


def _resolve_pull_date_range(args, start_time: str, end_time: str, today: str) -> tuple:
    """从已解析的 start_time/end_time 取 YYYY-MM-DD（与顶部时间横幅一致）。"""
    if start_time and end_time:
        start_date = start_time.split(' ')[0]
        end_date = end_time.split(' ')[0]
        return start_date, end_date
    start_date = args.start or today
    end_date = args.end or args.start or today
    return start_date, end_date


def _effective_interval_seconds(service_name: str, interval: Optional[int]) -> int:
    """日粒度接口忽略 interval，避免同一天被拉 N 次。"""
    from common.wdt_pull_policy import is_wdt_day_only_service

    if not interval or interval <= 0:
        return 0
    if is_wdt_day_only_service(service_name):
        print(
            f'\n[警告] {service_name} 仅支持按天查询，已忽略 --interval {interval}'
            f'（避免同一天重复拉取）\n',
            flush=True,
        )
        logger.warning('忽略 interval=%s，service=%s 为日粒度接口', interval, service_name)
        return 0
    return int(interval)


def _resolve_connector_for_service(connector: str, service_name: str) -> str:
    """服务在连接器间迁移后，旧的 -c 参数仍可用（如 wdt.hjy.* 已挪到 hjy）。"""
    from connectors import resolve_connector

    actual = resolve_connector(connector, service_name)
    if actual != connector:
        print(f'[提示] 服务 {service_name} 属于连接器 {actual}，已自动从 {connector} 切换')
        logger.info('连接器自动校正: %s -> %s (service=%s)', connector, actual, service_name)
    return actual


def pull_command(args):
    """执行数据拉取"""
    service_name = args.service
    connector = _resolve_connector_for_service(args.connector, service_name)

    today = datetime.now().strftime('%Y-%m-%d')
    from common.past_range import resolve_past_amount, compute_past_time_range
    past_amount, past_unit = resolve_past_amount({
        'past_value': getattr(args, 'past', None),
        'past_days': getattr(args, 'past_days', None),
        'past_unit': getattr(args, 'past_unit', None),
    })
    if past_amount is not None:
        start_time, end_time = compute_past_time_range(past_amount, past_unit)
    else:
        if connector == 'hjy' and service_name in (
            'sht_recon_detail', 'recon_delivery_detail', 'recon_dztk_summary',
        ) and args.start is None and args.end is None:
            start_time = None
            end_time = None
        elif connector == 'hjy' and service_name in (
            'sht_recon_detail', 'recon_delivery_detail', 'recon_dztk_summary',
        ):
            s = args.start or args.end or today
            e = args.end or args.start or today
            start_time = s if ' ' in s else f"{s} 00:00:00"
            end_time = e if ' ' in e else f"{e} 23:59:59"
        elif connector == 'wdt' and service_name == 'logistics_trace' and getattr(args, 'logistics_no', None) and args.start is None and args.end is None:
            start_time = None
            end_time = None
        else:
            s = args.start or today
            e = args.end or today
            start_time = s if ' ' in s else f"{s} 00:00:00"
            end_time = e if ' ' in e else f"{e} 23:59:59"
    
    print(f"\n{'='*60}")
    print(f"数据拉取任务")
    print(f"{'='*60}")
    print(f"连接器: {connector}")
    print(f"服务:   {service_name}")
    if start_time is None and end_time is None:
        print(f"时间:   未指定（不传 startDate/endDate）")
    else:
        print(f"时间:   {start_time} ~ {end_time}")
    interval_effective = _effective_interval_seconds(service_name, args.interval)
    if interval_effective:
        print(f"间隔:   {interval_effective} 秒")
    print(f"{'='*60}\n")

    pull_kwargs = {
        'shop_no': args.shop_no,
        'page_size': args.page_size,
        'max_workers': args.workers,
        'classification_name': getattr(args, 'classification_name', None),
        'start_config_record_time': getattr(args, 'start_config_record_time', None),
        'end_config_record_time': getattr(args, 'end_config_record_time', None),
        'is_summary': getattr(args, 'is_summary', '0'),
        'scheme_name': getattr(args, 'scheme_name', None),
        'terms_income': getattr(args, 'terms_income', None),
        'composite_dim': getattr(args, 'composite_dim', None),
        'split_suite': getattr(args, 'split_suite', None),
        'cost_type': getattr(args, 'cost_type', None),
        'stat_mode': getattr(args, 'stat_mode', None),
        'order_way': getattr(args, 'order_way', None),
        'display_by_shop': getattr(args, 'display_by_shop', None),
        'display_by_date': getattr(args, 'display_by_date', None),
        'original_order': getattr(args, 'original_order', None),
        'plat_order_nos': getattr(args, 'plat_order_nos', None),
        'erp_order_nos': getattr(args, 'erp_order_nos', None),
        'shop_nos': getattr(args, 'shop_nos', None),
        'spec_no': getattr(args, 'spec_no', None),
        'project': getattr(args, 'project', None),
        'summary_no': getattr(args, 'summary_no', None),
        'expense_item_name': getattr(args, 'expense_item_name', None),
        'order_tools': getattr(args, 'order_tools', None),
        'warehouse_no': getattr(args, 'warehouse_no', None),
        'goods_no': getattr(args, 'goods_no', None),
        'brand_name': getattr(args, 'brand_name', None),
        'class_name': getattr(args, 'class_name', None),
        'barcode': getattr(args, 'barcode', None),
        'hide_deleted': getattr(args, 'hide_deleted', None),
        'period_mark': getattr(args, 'period_mark', None),
        'reco_status': getattr(args, 'reco_status', None),
        'refund_type': getattr(args, 'refund_type', None),
        'salesman_name': getattr(args, 'salesman_name', None),
        'start_business_time': getattr(args, 'start_business_time', None),
        'end_business_time': getattr(args, 'end_business_time', None),
        'author_name': getattr(args, 'author_name', None),
        'oms_stockout_no': getattr(args, 'oms_stockout_no', None),
        'oms_order_no': getattr(args, 'oms_order_no', None),
        'province_names': getattr(args, 'province_names', None),
        'city_names': getattr(args, 'city_names', None),
        'district_names': getattr(args, 'district_names', None),
        'goods_batch_no': getattr(args, 'goods_batch_no', None),
        'refund_stage': getattr(args, 'refund_stage', None),
        'time_type': getattr(args, 'time_type', None),
        'stockin_no': getattr(args, 'stockin_no', None),
        'refund_no': getattr(args, 'refund_no', None),
        'status': getattr(args, 'status', None),
        'need_sn': getattr(args, 'need_sn', None),
        'logistics_no': getattr(args, 'logistics_no', None),
        'logistics_status': getattr(args, 'logistics_status', None),
        'need_detail': getattr(args, 'need_detail', False),
    }
    pull_kwargs = {k: v for k, v in pull_kwargs.items() if v is not None}
    
    # 微伴 external_user 服务优先使用 database(mysql) 配置
    if connector == 'weiban' and service_name == 'external_user':
        cfg = get_config()
        mysql_db_conf = cfg.get('database(mysql)')
        if isinstance(mysql_db_conf, dict) and mysql_db_conf:
            cfg.database = DatabaseConfig(
                type=mysql_db_conf.get('type', cfg.database.type),
                host=mysql_db_conf.get('host', cfg.database.host),
                port=mysql_db_conf.get('port', cfg.database.port),
                user=mysql_db_conf.get('user', cfg.database.user),
                password=mysql_db_conf.get('password', cfg.database.password),
                database=mysql_db_conf.get('database', cfg.database.database),
                charset=mysql_db_conf.get('charset', cfg.database.charset),
                driver=mysql_db_conf.get('driver', cfg.database.driver),
                pool_size=mysql_db_conf.get('pool_size', cfg.database.pool_size),
            )
            reset_db_manager(cfg)

    # 创建服务
    if connector == 'wdt':
        from connectors.wdt import create_service
        service = create_service(service_name)
    elif connector == 'hjy':
        from connectors.hjy import create_service
        service = create_service(service_name)
    elif connector == 'weiban':
        if service_name == 'external_user':
            from connectors.weiban.services import ExternalUserPullService
            service = ExternalUserPullService()
        elif service_name == 'external_user_detail':
            from connectors.weiban.services import ExternalUserDetailPullService
            service = ExternalUserDetailPullService()
        else:
            print(f"未知的服务: {service_name}")
            print(f"微伴连接器支持的服务: external_user, external_user_detail")
            return 1
    else:
        print(f"未知的连接器: {connector}")
        print(f"支持的连接器: wdt, hjy, weiban")
        return 1
    
    # 执行拉取
    try:
        # 微伴连接器使用特殊的拉取方法（实时接口，不支持时间范围）
        if connector == 'weiban' and service_name == 'external_user':
            # 微伴接口是实时的，只支持 pull_today() 方法
            if args.start and args.end and (args.start != args.end or ' ' in args.start):
                print("\n⚠️  警告: 微伴接口是实时的，不支持时间范围参数")
                print("   将忽略时间参数，拉取当前所有客户数据\n")
            
            # 优先使用 staff_ids，如果没有则使用 shop_no
            staff_ids = args.staff_ids if hasattr(args, 'staff_ids') and args.staff_ids else None
            staff_id = args.shop_no if not staff_ids else None
            use_ehr = not (hasattr(args, 'no_ehr') and args.no_ehr)  # 默认从 EHR 读取
            
            result = service.pull_today(
                debug=args.debug,
                staff_id=staff_id,
                staff_ids=staff_ids,
                use_ehr=use_ehr,
                max_workers=args.workers
            )
        elif connector == 'weiban' and service_name == 'external_user_detail':
            # 客户详情拉取
            result = service.pull_today(
                debug=args.debug,
                max_workers=args.workers
            )
        elif connector == 'hjy' and service_name in (
            'bill_standard', 'bk_share_data', 'fixbill_data_summary',
            'sht_recon_detail', 'recon_delivery_detail', 'hjy_delivery_detail',
            'recon_delivery_summary', 'recon_return_storage_summary',
            'recon_order_confirm_summary', 'recon_dztk_summary',
            'marketing_share_result', 'expense_sku_day_summary', 'expense_sku_share_day_detail',
            'profits_sku', 'profits_order', 'profits_live_sku', 'profits_live_order', 'profits_live_refund',
            'marketing_detail',
        ):
            from common.wdt_pull_policy import is_wdt_day_only_service

            if is_wdt_day_only_service(service_name):
                pull_start_date, pull_end_date = _resolve_pull_date_range(args, start_time, end_time, today)
                result = service.pull_by_day(
                    start_date=pull_start_date,
                    end_date=pull_end_date,
                    interval_seconds=0,
                    debug=args.debug,
                    **pull_kwargs,
                )
            elif interval_effective > 0:
                result = service.pull_by_interval(
                    start_time=start_time,
                    end_time=end_time,
                    interval_seconds=interval_effective,
                    debug=args.debug,
                    **pull_kwargs,
                )
            elif args.by_day:
                result = service.pull_by_day(
                    start_date=args.start or today,
                    end_date=args.end or args.start or today,
                    interval_seconds=0,
                    debug=args.debug,
                    **pull_kwargs,
                )
            else:
                result = service.pull(
                    start_time=start_time,
                    end_time=end_time,
                    debug=args.debug,
                    **pull_kwargs,
                )
        elif interval_effective > 0:
            result = service.pull_by_interval(
                start_time=start_time,
                end_time=end_time,
                interval_seconds=interval_effective,
                debug=args.debug,
                **pull_kwargs,
            )
        elif args.by_day:
            result = service.pull_by_day(
                start_date=args.start or today,
                end_date=args.end or args.start or today,
                interval_seconds=0,
                debug=args.debug,
                **pull_kwargs,
            )
        else:
            result = service.pull(
                start_time=start_time,
                end_time=end_time,
                debug=args.debug,
                **pull_kwargs,
            )
        
        print(f"\n{'='*60}")
        print("拉取完成！")
        print(f"  获取: {result.fetched} 条")
        print(f"  保存: {result.saved} 条")
        print(f"  错误: {result.errors} 条")
        print(f"  耗时: {result.duration:.2f} 秒")
        
        # 微伴连接器的额外统计信息
        if connector == 'weiban' and 'new_joined' in result.details:
            print(f"  新加入: {result.details.get('new_joined', 0)} 条")
            print(f"  标记流失: {result.details.get('outflow_marked', 0)} 条")
        
        print(f"{'='*60}\n")
        
        return 0 if result.success else 1
        
    except Exception as e:
        logger.error(f"拉取失败: {e}")
        print(f"\n拉取失败: {e}")
        return 1


def list_command(args):
    """列出可用的连接器和服务"""
    from connectors import list_connectors
    
    connectors = list_connectors()
    
    print("\n可用的连接器和服务:")
    print("="*50)
    
    for name, info in connectors.items():
        enabled = "+" if get_config().is_connector_enabled(name) else "-"
        print(f"\n[{enabled}] {info.get('display_name', name)} ({name})")
        print(f"    版本: {info.get('version', 'unknown')}")
        
        services = info.get('services', {})
        if services:
            print("    服务:")
            for svc_name, svc_info in services.items():
                if isinstance(svc_info, dict):
                    print(f"      - {svc_name}: {svc_info.get('name', '')}")
                else:
                    print(f"      - {svc_name}")
    
    print()
    return 0


def dwd_command(args):
    # 直播利润类服务已迁到 hjy，清洗实现仍在 connectors.wdt.dwd_cleanse
    if args.connector not in ('wdt', 'hjy'):
        print(f'暂不支持的连接器: {args.connector}')
        return 1
    try:
        from connectors.wdt.dwd_cleanse import ALL_DWD_TASK_NAMES, run_dwd_task
        if args.task not in ALL_DWD_TASK_NAMES:
            print(f'未知任务: {args.task}，可选: {list(ALL_DWD_TASK_NAMES)}')
            return 1
        n = run_dwd_task(args.task, debug=getattr(args, 'debug', False))
        print(f'DWD {args.task}: 写入 {n} 行')
        return 0
    except Exception as e:
        logger.error(f'DWD 失败: {e}')
        print(f'DWD 失败: {e}')
        return 1


def bi_command(args):
    import bi.tasks  # noqa: F401 — 注册任务
    from bi import list_tasks, run_bi_task

    if getattr(args, 'list_tasks', False):
        tasks = list_tasks()
        print('\n可用的 BI 报表任务:')
        print('=' * 50)
        for t in tasks:
            print(f'  {t.name}')
            print(f'    名称: {t.label}')
            print(f'    说明: {t.description}')
            table_ref = f"{t.target_database}.dbo.{t.target_table}" if t.target_database else t.target_table
            print(f'    结果表: {table_ref}')
            print(f'    日期列: {t.date_column}')
            print()
        return 0

    task_name = (args.task or '').strip()
    if not task_name:
        print('请指定任务: -t / --task，或使用 --list 查看')
        return 1

    try:
        n = run_bi_task(
            task_name,
            start_date=args.start,
            end_date=args.end,
            past_value=getattr(args, 'past', None),
            past_unit=getattr(args, 'past_unit', None),
            past_days=getattr(args, 'past_days', None),
            mode=getattr(args, 'mode', 'auto') or 'auto',
            debug=getattr(args, 'debug', False),
        )
        print(f'BI {task_name}: 写入 {n} 行')
        return 0
    except Exception as e:
        logger.error(f'BI 失败: {e}')
        print(f'BI 失败: {e}')
        return 1


def operant_command(args):
    import operant.tasks  # noqa: F401
    from operant import list_tasks, run_operant_task

    if getattr(args, 'list_tasks', False):
        tasks = list_tasks()
        print('\n可用的 OperantID 实验任务:')
        print('=' * 50)
        for t in tasks:
            print(f'  {t.name}')
            print(f'    名称: {t.label}')
            print(f'    说明: {t.description}')
            print(f'    结果表: operant_{t.target_table}')
            print(f'    唯一键: {t.unique_key}')
            print()
        return 0

    task_name = (args.task or '').strip()
    if not task_name:
        print('请指定任务: -t / --task，或使用 --list 查看')
        return 1
    try:
        n = run_operant_task(
            task_name,
            account=getattr(args, 'account', None),
            start=args.start,
            end=args.end,
            past_value=getattr(args, 'past', None),
            past_unit=getattr(args, 'past_unit', None),
            past_days=getattr(args, 'past_days', None),
            instruction=getattr(args, 'instruction', None),
            login_url=getattr(args, 'login_url', None),
            target_table=getattr(args, 'target_table', None),
            unique_key=getattr(args, 'unique_key', None),
            headless=False if getattr(args, 'headed', False) else None,
            debug=getattr(args, 'debug', False),
        )
        print(f'OperantID {task_name}: 写入 {n} 行')
        return 0
    except Exception as e:
        logger.error(f'OperantID 失败: {e}')
        print(f'OperantID 失败: {e}')
        return 1


def stats_command(args):
    """显示统计信息"""
    try:
        from utils.task_queue import get_task_queue
        queue = get_task_queue()
        
        if queue:
            stats = queue.get_queue_stats()
            print("\n队列统计:")
            print(f"  重试队列: {stats['retry_queue_length']} 个任务")
            print(f"  死信队列: {stats['dead_queue_length']} 个任务")
        else:
            print("\nRedis 未配置，无法获取队列统计")
    except ImportError:
        print("\n任务队列模块不可用")
    
    return 0


def cli():
    """构建 CLI 解析器"""
    parser = argparse.ArgumentParser(
        prog='data-sync',
        description='数据同步平台 - 多系统数据拉取工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 拉取旺店通今日订单
  python -m cli pull --connector wdt --service trade
  
  # 拉取微伴当前客户数据（实时接口）
  python -m cli pull -c weiban -s external_user
  
  # 拉取指定日期范围（仅 wdt）
  python -m cli pull -c wdt -s trade --start 2025-12-01 --end 2025-12-07
  
  # 拉取过去7天的数据（仅 wdt）
  python -m cli pull -c wdt -s trade --past-days 7 --interval 3600
  
  # 按小时间隔拉取（仅 wdt）
  python -m cli pull -c wdt -s trade --start 2025-12-01 --end 2025-12-01 --interval 3600
  
  # 列出所有可用的连接器
  python -m cli list
  
注意:
  - 微伴接口是实时的，不支持时间范围参数
  - 微伴总是返回当前所有未流失客户
  - --past-days 优先于 --start/--end 参数
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # ========== pull 命令 ==========
    pull_parser = subparsers.add_parser('pull', help='拉取数据')
    
    # 必选参数
    pull_parser.add_argument(
        '-c', '--connector',
        required=True,
        help='连接器名称（wdt / hjy / weiban）'
    )
    pull_parser.add_argument(
        '-s', '--service',
        required=True,
        help='服务名称（wdt: trade/refund/…; hjy: bill_standard/recon_delivery_summary/…; weiban: external_user）'
    )
    
    # 时间参数（不传则默认当天；sht_recon_detail/recon_delivery_detail/recon_dztk_summary 同时不传 --start/--end 则不传账期日期参数）
    pull_parser.add_argument(
        '--start',
        default=None,
        help='开始时间 (YYYY-MM-DD 或 "YYYY-MM-DD HH:MM:SS")'
    )
    pull_parser.add_argument(
        '--end',
        default=None,
        help='结束时间'
    )
    pull_parser.add_argument(
        '--past-days',
        type=int,
        help='拉取过去N天的数据（兼容旧参数，等同 --past N --past-unit day）'
    )
    pull_parser.add_argument(
        '--past',
        type=float,
        default=None,
        help='回溯时间数值（配合 --past-unit，优先于 --start/--end）'
    )
    pull_parser.add_argument(
        '--past-unit',
        default='day',
        choices=['second', 'minute', 'hour', 'day', 'week', 'month'],
        help='回溯时间单位，默认 day'
    )
    
    # 可选参数
    pull_parser.add_argument(
        '--interval', '-i',
        type=int,
        default=0,
        help='时间间隔（秒），如 3600=1小时，0=整体拉取'
    )
    pull_parser.add_argument(
        '--by-day', '-d',
        action='store_true',
        help='按天循环拉取'
    )
    pull_parser.add_argument(
        '--shop-no',
        help='店铺编号（wdt）或员工ID（weiban，单个）'
    )
    pull_parser.add_argument(
        '--classification-name',
        help='费用项名称（仅 bk_share_data/fixbill_data_summary）'
    )
    pull_parser.add_argument(
        '--start-config-record-time',
        help='配置录入开始日期（仅 bk_share_data/fixbill_data_summary）'
    )
    pull_parser.add_argument(
        '--end-config-record-time',
        help='配置录入结束日期（仅 bk_share_data/fixbill_data_summary）'
    )
    pull_parser.add_argument(
        '--is-summary',
        default='0',
        help='是否汇总数据，0=明细，1=汇总（仅 bk_share_data/fixbill_data_summary）'
    )
    pull_parser.add_argument(
        '--staff-ids',
        help='员工ID列表（weiban，多个用逗号分隔，如：hlw487,hlw488）'
    )
    pull_parser.add_argument(
        '--no-ehr',
        action='store_true',
        help='weiban：不从 EHR 数据库读取员工ID，拉取全量数据'
    )
    pull_parser.add_argument(
        '--scheme-name',
        default=None,
        help='方案名称（利润表接口）'
    )
    pull_parser.add_argument(
        '--terms-income',
        default=None,
        help='查询口径（利润表接口）'
    )
    pull_parser.add_argument(
        '--composite-dim',
        default=None,
        help='查询维度（商品利润表默认1，订单利润表默认7）'
    )
    pull_parser.add_argument(
        '--split-suite',
        default='1',
        help='是否拆分组合装：是1/否0（利润表接口）'
    )
    pull_parser.add_argument(
        '--cost-type',
        help='成本类型代码（利润表接口）'
    )
    pull_parser.add_argument(
        '--stat-mode',
        help='是否跟单：不跟单0/跟单1（利润表接口）'
    )
    pull_parser.add_argument(
        '--order-way',
        help='建单方式：手工建单0/平台建单1（利润表接口）'
    )
    pull_parser.add_argument(
        '--display-by-shop',
        help='是否按店铺展示：是1/否0（商品利润表）'
    )
    pull_parser.add_argument(
        '--display-by-date',
        help='是否按时间展示：是1/否0（商品利润表）'
    )
    pull_parser.add_argument(
        '--original-order',
        default='1',
        help='按原始单+系统单展示：是1/否0（订单利润表）'
    )
    pull_parser.add_argument(
        '--plat-order-nos',
        help='平台订单号，逗号分隔（订单利润表）'
    )
    pull_parser.add_argument(
        '--erp-order-nos',
        help='系统订单号，逗号分隔（订单利润表）'
    )
    pull_parser.add_argument(
        '--shop-nos',
        help='店铺编码，逗号分隔（利润表接口、expense_sku_share_day_detail）'
    )
    pull_parser.add_argument(
        '--spec-no',
        help='商家编码（仅 marketing_share_result）'
    )
    pull_parser.add_argument(
        '--project',
        type=int,
        help='费用项编码（仅 marketing_share_result）'
    )
    pull_parser.add_argument(
        '--summary-no',
        help='汇总单号，逗号分隔（expense_sku_day_summary / expense_sku_share_day_detail）'
    )
    pull_parser.add_argument(
        '--expense-item-name',
        help='费用项名称，逗号分隔（仅 expense_sku_day_summary）'
    )
    pull_parser.add_argument(
        '--order-tools',
        help='订单渠道（仅 profits_live_order/profits_live_refund，如 1 或 1,2,3,4）'
    )
    pull_parser.add_argument(
        '--warehouse-no',
        help='仓库编号（出库单；发货对账明细支持逗号多仓）'
    )
    pull_parser.add_argument(
        '--goods-no',
        help='货品编号（goods_query_with_spec）'
    )
    pull_parser.add_argument(
        '--brand-name',
        help='品牌名称（goods_query_with_spec）'
    )
    pull_parser.add_argument(
        '--class-name',
        help='分类名称（goods_query_with_spec）'
    )
    pull_parser.add_argument(
        '--barcode',
        help='条码（goods_query_with_spec）'
    )
    pull_parser.add_argument(
        '--hide-deleted',
        type=int,
        choices=[0, 1],
        default=None,
        help='是否隐藏已删除：0全部/1隐藏（goods_query_with_spec，默认1）'
    )
    pull_parser.add_argument(
        '--time-type',
        type=int,
        default=None,
        help='时间条件类型：0修改时间/1入库时间（stockin_refund_openapi，默认0）'
    )
    pull_parser.add_argument(
        '--stockin-no',
        default=None,
        help='入库单号（stockin_refund_openapi）'
    )
    pull_parser.add_argument(
        '--refund-no',
        default=None,
        help='退换单号（stockin_refund_openapi）'
    )
    pull_parser.add_argument(
        '--status',
        default=None,
        help='入库单状态，逗号分隔：10已取消,20编辑中,30待审核,80已完成（stockin_refund_openapi）'
    )
    pull_parser.add_argument(
        '--need-sn',
        default=None,
        help='是否返回SN：true/false（stockin_refund_openapi）'
    )
    pull_parser.add_argument(
        '--period-mark',
        default=None,
        help='对账标识 periodMark（慧经营对账类接口，如 1）'
    )
    pull_parser.add_argument(
        '--reco-status',
        default=None,
        help='对账状态，逗号分隔（如 对账成功,对账失败）'
    )
    parser.add_argument(
        '--refund-type',
        default=None,
        help='退款类型，逗号分隔（如 已取消,退货入库,仅退款；recon_dztk_summary 对应 refundTypes）'
    )
    pull_parser.add_argument(
        '--salesman-name',
        default=None,
        help='业务员名称（发货对账明细）'
    )
    pull_parser.add_argument(
        '--start-business-time',
        default=None,
        help='业务开始时间（发货对账/慧经营发货明细，如 2026-01-01 00:00:00）'
    )
    pull_parser.add_argument(
        '--end-business-time',
        default=None,
        help='业务结束时间（发货对账/慧经营发货明细）'
    )
    pull_parser.add_argument(
        '--author-name',
        default=None,
        help='达人名称（hjy_delivery_detail）'
    )
    pull_parser.add_argument(
        '--oms-stockout-no',
        default=None,
        help='出库单号，逗号分隔（hjy_delivery_detail）'
    )
    pull_parser.add_argument(
        '--oms-order-no',
        default=None,
        help='系统订单号，逗号分隔（hjy_delivery_detail）'
    )
    pull_parser.add_argument(
        '--province-names',
        default=None,
        help='省，逗号分隔（hjy_delivery_detail）'
    )
    pull_parser.add_argument(
        '--city-names',
        default=None,
        help='市，逗号分隔（hjy_delivery_detail）'
    )
    pull_parser.add_argument(
        '--district-names',
        default=None,
        help='区，逗号分隔（慧经营发货类接口）'
    )
    pull_parser.add_argument(
        '--goods-batch-no',
        default=None,
        help='货品批次号（recon_return_storage_summary）'
    )
    pull_parser.add_argument(
        '--refund-stage',
        default=None,
        help='退款阶段：售中/售后（recon_return_storage_summary）'
    )
    pull_parser.add_argument(
        '--logistics-no',
        default=None,
        help='物流单号（物流轨迹查询，传入时可不传时间）'
    )
    pull_parser.add_argument(
        '--logistics-status',
        type=int,
        default=None,
        help='物流状态（物流轨迹查询，默认5已签收）'
    )
    pull_parser.add_argument(
        '--need-detail',
        action='store_true',
        help='返回物流详情（物流轨迹查询，page_size最大100）'
    )
    pull_parser.add_argument(
        '--page-size', '-ps',
        type=int,
        default=200,
        help='每页数量'
    )
    pull_parser.add_argument(
        '--workers', '-w',
        type=int,
        default=10,
        help='并行线程数'
    )
    pull_parser.add_argument(
        '--debug',
        action='store_true',
        help='打印调试信息'
    )
    pull_parser.add_argument(
        '--schedule',
        help='定时执行，格式 HH:MM，如 01:00 表示每天凌晨1点执行'
    )
    
    pull_parser.set_defaults(func=pull_command)
    
    dwd_parser = subparsers.add_parser('dwd', help='ODS 清洗写入 DWD（SQL Server）')
    dwd_parser.add_argument('-c', '--connector', default='wdt', help='连接器，默认 wdt')
    dwd_parser.add_argument(
        '-t', '--task',
        required=True,
        help='清洗任务',
    )
    dwd_parser.add_argument('--debug', action='store_true', help='打印 DWD 执行 SQL（入 core 日志）')
    dwd_parser.set_defaults(func=dwd_command)

    bi_parser = subparsers.add_parser('bi', help='BI 报表计算（库内 SQL → 结果表）')
    bi_parser.add_argument('-t', '--task', help='BI 任务名')
    bi_parser.add_argument('--list', action='store_true', dest='list_tasks', help='列出所有 BI 任务')
    bi_parser.add_argument('--start', help='开始日期 YYYY-MM-DD')
    bi_parser.add_argument('--end', help='结束日期 YYYY-MM-DD')
    bi_parser.add_argument('--past', type=float, help='回溯数值（与 --past-unit 配合）')
    bi_parser.add_argument('--past-days', type=int, help='回溯天数（兼容旧参数）')
    bi_parser.add_argument(
        '--past-unit',
        choices=['second', 'minute', 'hour', 'day', 'week', 'month'],
        default='day',
        help='回溯单位，默认 day',
    )
    bi_parser.add_argument(
        '--mode',
        choices=['auto', 'full', 'window'],
        default='auto',
        help='auto=首次全量/后期窗口增量; full=清空后重算; window=仅重算日期窗口',
    )
    bi_parser.add_argument('--debug', action='store_true', help='打印执行 SQL')
    bi_parser.set_defaults(func=bi_command)

    operant_parser = subparsers.add_parser('operant', help='OperantID 实验：浏览器登录下载并入库')
    operant_parser.add_argument('-t', '--task', help='OperantID 任务名')
    operant_parser.add_argument('--list', action='store_true', dest='list_tasks', help='列出所有 OperantID 任务')
    operant_parser.add_argument('--account', help='config.yaml operantid.accounts 中的帐号名')
    operant_parser.add_argument('--login-url', help='覆盖登录地址')
    operant_parser.add_argument('--instruction', help='额外下载指令')
    operant_parser.add_argument('--target-table', help='覆盖目标表（写入 operant_<name>）')
    operant_parser.add_argument('--unique-key', help='覆盖唯一键，默认 rowKey')
    operant_parser.add_argument('--start', help='开始日期 YYYY-MM-DD')
    operant_parser.add_argument('--end', help='结束日期 YYYY-MM-DD')
    operant_parser.add_argument('--past', type=float, help='回溯数值（与 --past-unit 配合）')
    operant_parser.add_argument('--past-days', type=int, help='回溯天数（兼容旧参数）')
    operant_parser.add_argument(
        '--past-unit',
        choices=['second', 'minute', 'hour', 'day', 'week', 'month'],
        default='day',
        help='回溯单位，默认 day',
    )
    operant_parser.add_argument('--headed', action='store_true', help='显示浏览器窗口（调试用）')
    operant_parser.add_argument('--debug', action='store_true', help='打印任务指令与入库细节')
    operant_parser.set_defaults(func=operant_command)

    # ========== list 命令 ==========
    list_parser = subparsers.add_parser('list', help='列出可用的连接器和服务')
    list_parser.set_defaults(func=list_command)
    
    # ========== stats 命令 ==========
    stats_parser = subparsers.add_parser('stats', help='显示队列统计')
    stats_parser.set_defaults(func=stats_command)
    
    return parser


def _calc_next_run(target_time_str: str) -> float:
    now = datetime.now()
    h, m = map(int, target_time_str.split(':'))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def _scheduled_pull(args):
    schedule_time = args.schedule
    try:
        h, m = map(int, schedule_time.split(':'))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except (ValueError, AttributeError):
        print(f"无效的时间格式: {schedule_time}，请使用 HH:MM 格式")
        return 1

    print(f"定时任务已启动，每天 {schedule_time} 执行")
    while True:
        wait = _calc_next_run(schedule_time)
        next_run = datetime.now() + timedelta(seconds=wait)
        print(f"下次执行: {next_run.strftime('%Y-%m-%d %H:%M:%S')} (等待 {wait:.0f} 秒)")
        time.sleep(wait)
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行定时拉取...")
        pull_command(args)


def main():
    """CLI 入口"""
    parser = cli()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    if args.command == 'pull' and args.schedule:
        return _scheduled_pull(args)
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

