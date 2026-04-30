# -*- coding: utf-8 -*-
import json
import sys
sys.path.insert(0, '.')

from connectors.wdt.client import get_wdt_client
from connectors.wdt.sdk.api import StockoutStatusType
from datetime import datetime, timedelta

client = get_wdt_client()
api = client.stockout_sales_query_with_detail_api

end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
start_time = (datetime.now() - timedelta(minutes=60)).strftime('%Y-%m-%d %H:%M:%S')

print(f"查询时间: {start_time} ~ {end_time}")

result = api.query(
    start_time=start_time,
    end_time=end_time,
    status_type=StockoutStatusType.DELAYED_AND_COMPLETED,
    page_size=5,
    page_no=1,
    debug=True
)

if str(result.get('status')) != '0':
    print(f"API错误: {result.get('message')}")
    sys.exit(1)

orders = result.get('data', {}).get('order', [])
print(f"\n获取到 {len(orders)} 条出库单")

if not orders:
    print("无数据，尝试扩大时间范围")
    sys.exit(0)

print(f"\n=== 第一条出库单全部字段 ===")
first = orders[0]
for k, v in first.items():
    if k in ('details_list', 'detail_list', 'order_detail_list'):
        v = f"[{len(v) if isinstance(v, list) else '...'}条明细]"
    print(f"  {k}: {v}")

print(f"\n=== fenxiao_nick_no 字段检查 ===")
has_value = 0
for i, order in enumerate(orders):
    val = order.get('fenxiao_nick_no')
    if val and str(val).strip():
        has_value += 1
        if has_value <= 3:
            print(f"  订单[{i}] stockout_id={order.get('stockout_id')}: fenxiao_nick_no={val}")

print(f"\n结果: {len(orders)} 条中有 {has_value} 条 fenxiao_nick_no 有值")
if has_value == 0:
    print("=> 接口本身就没返回 fenxiao_nick_no 数据，不是代码问题")
else:
    print("=> 接口有数据，需要检查入库逻辑")
