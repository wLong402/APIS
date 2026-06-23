# 数据同步平台

模块化的多系统数据拉取平台，支持旺店通等系统的数据同步。

## 项目结构

```
data_sync_platform/
├── run.py                    # 入口文件
├── config/
│   └── config.yaml           # 配置文件
├── cli/                      # 命令行接口
│   └── main.py
├── core/                     # 核心模块
│   ├── config.py             # 配置管理
│   ├── database.py           # 数据库
│   ├── logger.py             # 日志
│   └── exceptions.py         # 异常
├── common/                   # 通用基类
│   ├── base_client.py        # API客户端基类
│   ├── base_service.py       # 服务基类
│   └── base_repository.py    # 数据仓库基类
├── connectors/               # 连接器（各系统适配）
│   └── wdt/                  # 旺店通连接器
│       ├── client.py
│       ├── services/
│       └── repositories/
├── wdt/                      # 旺店通SDK（底层API）
│   ├── config.py
│   ├── client.py
│   ├── sign.py
│   └── api/
├── utils/                    # 工具模块
│   ├── logger.py
│   └── task_queue.py
├── api/                      # REST API（预留）
├── scheduler/                # 任务调度（预留）
├── logs/                     # 日志目录
├── docs/                     # 文档
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── docker/
    └── entrypoint.sh
```

## Docker 部署

### 1. 准备配置

```bash
cp config/config.docker.example.yaml config/config.yaml
# 编辑 config/config.yaml，填写 API 密钥与数据库连接
# 容器内 Redis 主机名固定为 redis（已在示例配置中设置）
# 数据库在宿主机时使用 host.docker.internal
```

可选：复制环境变量模板

```bash
cp .env.example .env
```

### 2. 启动服务

```bash
docker compose up -d --build
```

- Web 控制台: http://localhost:8765
- Redis: localhost:6379（任务队列 / 重试）

查看日志：

```bash
docker compose logs -f web
```

### 3. 一次性 CLI 拉取

```bash
docker compose --profile cli run --rm cli pull -c wdt -s trade --start 2025-12-01 --end 2025-12-07
```

### 4. 常用命令

```bash
# 停止
docker compose down

# 重建镜像
docker compose build --no-cache web

# 进入容器
docker compose exec web bash
```

说明：

- `config/`、`logs/`、`tokens/`（Token 缓存）通过 volume 挂载，容器重启不丢
- 环境变量 `CONFIG_PATH`、`REDIS_HOST`、`REDIS_PORT` 可覆盖配置（见 `.env.example`）
- SQL Server 需使用镜像内已安装的 `ODBC Driver 18 for SQL Server`

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

编辑 `config/config.yaml`：

```yaml
wdt:
  app_key: 'your_app_key'
  app_secret: 'your_secret:your_salt'
  qimen_appkey: 'your_qimen_appkey'
  qimen_appsecret: 'your_qimen_secret'
  gateway_url: 'http://xxx.api.taobao.com/router/qm'
  target_appkey: 'target_appkey'
  wdt3_customer_id: 'customer_id'

# MySQL 数据库
database:
  type: mysql
  host: localhost
  port: 3306
  user: root
  password: ''
  database: data_sync
  charset: utf8mb4

# SQL Server 数据库
database:
  type: sqlserver
  host: localhost
  port: 1433
  user: sa
  password: ''
  database: data_sync
  driver: ODBC Driver 17 for SQL Server
```

### 使用方式

```bash
# 查看帮助
python run.py --help

# 列出可用的连接器和服务
python run.py list

# 拉取旺店通原始订单
python run.py pull -c wdt -s trade --start 2025-12-01 --end 2025-12-07

# 拉取过去7天的数据
python run.py pull -c wdt -s trade --past-days 7 --interval 3600

# 按小时间隔拉取（推荐）
python run.py pull -c wdt -s trade --start 2025-12-01 --end 2025-12-01 --interval 3600

# 显示详细调试信息
python run.py pull -c wdt -s trade --start 2025-12-01 --end 2025-12-01 --interval 3600 --debug
```

## 可用服务

### 旺店通（wdt）服务列表

| 服务名称 | API接口 | 数据库表 | 说明 |
|---------|---------|----------|------|
| trade | wdt.sales.rawtrade.search | wdt_raw_trade<br>wdt_raw_trade_detail | 原始订单 |
| refund | wdt.aftersales.refund.rawrefund.search | wdt_raw_refund<br>wdt_raw_refund_detail | 退款单 |
| aftersales_refund | wdt.aftersales.refund.Refund.search | wdt_aftersales_refund | 售后退款单 |
| erp_trade | wdt.sales.tradequery.querywithdetail | wdt_erp_trade<br>wdt_erp_trade_detail | ERP订单 |
| stockout_sales_query_with_detail | wdt.wms.stockout.sales.querywithdetail | wdt_stockout_sales<br>wdt_stockout_sales_detail | 销售出库单（带明细） |
| stockin_refund_query_with_detail | wdt.wms.stockin.refund.querywithdetail | wdt_stockin_refund<br>wdt_stockin_refund_detail | 退货入库单（带明细） |
| stockspec | wdt.wms.stockspec.search | wdt_stockspec | 库存规格 |
| bill_standard | wdt.hjy.bill.billsatndard.query | wdt_bill_standard | 账单标准 |
| bk_share_data | wdt.hjy.bk.share.datas.query | wdt_bk_share_data | 日常记账分摊结果 |
| fixbill_data_summary | wdt.hjy.fixbill.datas.summary.query | wdt_fixbill_data_summary | 固定费用汇总数据 |
| marketing_detail | wdt.hjy.bill.marketing.detail.query | wdt_marketing_detail | 营销明细 |
| history_trade | wdt.sales.tradequery.queryhistorywithdetail | wdt_history_trade | 历史订单 |

### 命令示例

```bash
# 原始订单
python run.py pull -c wdt -s trade --start 2026-02-01 --end 2026-02-11 --interval 3600 --page-size 200 --workers 10 --debug

# 退款单
python run.py pull -c wdt -s refund --start 2026-02-01 --end 2026-02-11 --interval 3600 --page-size 200 --workers 10 --debug

# 售后退款单
python run.py pull -c wdt -s aftersales_refund --start 2026-02-01 --end 2026-02-11 --interval 3600 --page-size 200 --workers 10 --debug

# ERP订单
python run.py pull -c wdt -s erp_trade --start 2026-02-01 --end 2026-02-11 --interval 3600 --page-size 200 --workers 10 --debug

# 销售出库单（带明细）
python run.py pull -c wdt -s stockout_sales_query_with_detail --start 2026-02-01 --end 2026-02-11 --interval 3600 --page-size 200 --workers 3 --debug

# 退货入库单（带明细）
python run.py pull -c wdt -s stockin_refund_query_with_detail --start 2026-02-01 --end 2026-02-11 --interval 3600 --page-size 200 --workers 3 --debug

# 库存规格
python run.py pull -c wdt -s stockspec --start 2026-02-01 --end 2026-02-11 --interval 3600 --page-size 200 --workers 10 --debug

# 账单标准
python run.py pull -c wdt -s bill_standard --start 2026-02-01 --end 2026-02-11 --interval 3600 --page-size 200 --workers 5 --debug

# 日常记账分摊结果
python run.py pull -c wdt -s bk_share_data --start 2026-02-01 --end 2026-02-11 --page-size 200 --workers 5 --debug

# 固定费用汇总数据
python run.py pull -c wdt -s fixbill_data_summary --start 2026-02-01 --end 2026-02-11 --page-size 200 --workers 5 --debug

# 营销明细
python run.py pull -c wdt -s marketing_detail --start 2026-02-01 --end 2026-02-11 --interval 3600 --page-size 200 --workers 5 --debug

# 历史订单
python run.py pull -c wdt -s history_trade --start 2026-02-01 --end 2026-02-11 --interval 3600 --page-size 200 --workers 5 --debug
```

## 命令参数

```bash
python run.py pull [选项]

选项:
  -c, --connector   连接器名称（如 wdt）
  -s, --service     服务名称（如 trade）
  --start           开始日期（YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
  --end             结束日期
  --past-days       拉取过去N天的数据（如 7 表示过去7天，优先于 --start/--end）
  --interval        时间间隔（秒），如 3600 表示按小时
  --by-day          按天拉取
  --shop-no         店铺编号
  --classification-name  费用项名称（bk_share_data/fixbill_data_summary）
  --start-config-record-time  配置录入开始日期
  --end-config-record-time    配置录入结束日期
  --is-summary      是否汇总数据，0=明细，1=汇总
  --page-size       每页数量（默认200）
  --workers         并行线程数（默认10）
  --debug           显示调试信息
```

## 代码使用

### 使用服务拉取数据

```python
from connectors.wdt import create_service

# 创建服务
service = create_service('trade')

# 拉取数据
result = service.pull(
    start_time='2025-12-01 00:00:00',
    end_time='2025-12-01 23:59:59',
    page_size=200,
    max_workers=10,
    debug=True
)

print(f"获取: {result.fetched} 条")
print(f"保存: {result.saved} 条")
```

### 直接使用底层API

```python
from wdt import QimenClient, WdtConfig
from wdt.api import RawTradeSearchAPI

# 创建客户端
config = WdtConfig.from_yaml('config/config.yaml')
client = QimenClient(config)

# 创建API
api = RawTradeSearchAPI(client)

# 查询数据
result = api.search(
    start_time='2025-12-01 00:00:00',
    end_time='2025-12-01 23:59:59',
    page_size=50,
    page_no=1
)
```

## 扩展新连接器

1. 在 `connectors/` 下创建新目录（如 `jdy/`）
2. 实现 `client.py`（继承 `BaseAPIClient`）
3. 实现 `services/`（继承 `BasePullService`）
4. 实现 `repositories/`（继承 `BaseRepository`）
5. 在 `__init__.py` 中注册服务

详见 `docs/how_to_add_connector.md`

## 日志

- `logs/app.log` - 应用日志
- `logs/data_anomaly.log` - 数据异常日志（总数不匹配、空页等）

## 许可证 

MIT License
