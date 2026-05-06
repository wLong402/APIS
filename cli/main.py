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


def pull_command(args):
    """执行数据拉取"""
    from connectors.wdt import create_service
    
    connector = args.connector
    service_name = args.service
    
    today = datetime.now().strftime('%Y-%m-%d')
    # 时间处理
    if args.past_days:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=args.past_days)
        start_time = start_time.strftime('%Y-%m-%d 00:00:00')
        end_time = end_time.strftime('%Y-%m-%d 23:59:59')
    else:
        if connector == 'wdt' and service_name == 'sht_recon_detail' and args.start is None and args.end is None:
            start_time = None
            end_time = None
        elif connector == 'wdt' and service_name == 'sht_recon_detail':
            s = args.start or args.end or today
            e = args.end or args.start or today
            start_time = s if ' ' in s else f"{s} 00:00:00"
            end_time = e if ' ' in e else f"{e} 23:59:59"
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
    if args.interval:
        print(f"间隔:   {args.interval} 秒")
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
    }
    
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
        print(f"支持的连接器: wdt, weiban")
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
        elif connector == 'wdt' and service_name in ('bill_standard', 'bk_share_data', 'fixbill_data_summary', 'sht_recon_detail', 'marketing_share_result', 'expense_sku_day_summary'):
            result = service.pull(
                start_time=start_time,
                end_time=end_time,
                debug=args.debug,
                **pull_kwargs,
            )
        elif connector == 'wdt' and service_name in ('profits_sku', 'profits_order', 'profits_live_sku', 'profits_live_order', 'profits_live_refund'):
            result = service.pull_by_day(
                start_date=args.start or today,
                end_date=args.end or args.start or today,
                debug=args.debug,
                **pull_kwargs,
            )
        elif args.interval and args.interval > 0:
            result = service.pull_by_interval(
                start_time=start_time,
                end_time=end_time,
                interval_seconds=args.interval,
                debug=args.debug,
                **pull_kwargs,
            )
        elif args.by_day:
            result = service.pull_by_day(
                start_date=args.start or today,
                end_date=args.end or args.start or today,
                interval_seconds=args.interval or 0,
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
        help='连接器名称（如 wdt）'
    )
    pull_parser.add_argument(
        '-s', '--service',
        required=True,
        help='服务名称（wdt: trade, refund, stockout, erp_trade, stockin_refund, stockspec, bill_standard, bk_share_data, fixbill_data_summary, marketing_share_result, profits_sku, profits_order, profits_live_sku, profits_live_order, profits_live_refund; weiban: external_user, external_user_detail）'
    )
    
    # 时间参数（不传则默认当天；sht_recon_detail 同时不传 --start/--end 则不传账期日期参数）
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
        help='拉取过去N天的数据（如 7 表示过去7天，优先于 --start/--end）'
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
        help='店铺编码，逗号分隔（利润表接口）'
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
        help='汇总单号，逗号分隔（仅 expense_sku_day_summary）'
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
        help='仓库编号（仅出库单）'
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

