# 数据同步平台 - 架构说明

## 目录结构

```
data_sync_platform/
├── core/                   # 核心基础设施
│   ├── config.py          # 配置管理
│   ├── database.py        # 数据库管理
│   ├── logger.py          # 日志模块
│   └── exceptions.py      # 自定义异常
│
├── common/                 # 公共模块
│   ├── base_client.py     # API客户端基类
│   ├── base_service.py    # 服务基类
│   └── base_repository.py # 仓库基类
│
├── connectors/             # 连接器（各外部系统）
│   ├── wdt/               # 旺店通
│   │   ├── client.py      # 客户端
│   │   ├── services/      # 服务层
│   │   ├── repositories/  # 数据层
│   │   └── models/        # 数据模型
│   └── [其他系统]/         # 可扩展
│
├── cli/                    # 命令行接口
├── api/                    # Web API（预留）
├── scheduler/              # 任务调度（预留）
│
├── wdt/                    # 【旧】原有的wdt模块，保持不变
├── utils/                  # 【旧】原有的工具模块
├── main.py                 # 【旧】原有入口
└── run.py                  # 【新】新框架入口
```

## 核心概念

### 1. Connector（连接器）

每个外部系统对应一个连接器，包含：

- **Client**: API 客户端，负责与外部系统通信
- **Service**: 业务服务，实现数据拉取逻辑
- **Repository**: 数据仓库，负责数据存储

### 2. 添加新系统

1. 在 `connectors/` 下创建新目录
2. 实现 Client（继承 `BaseAPIClient`）
3. 实现 Service（继承 `BasePullService`）
4. 实现 Repository（继承 `BaseRepository`）
5. 在 `connectors/__init__.py` 中注册

### 3. 命名规范

- 表名：`{系统前缀}_{业务名}`，如 `wdt_raw_trade`
- 服务名：`{业务}PullService`，如 `TradePullService`
- 仓库名：`{业务}Repository`，如 `TradeRepository`

## 使用示例

```python
# 使用新框架拉取数据
from connectors.wdt import TradePullService

service = TradePullService()
result = service.pull(
    start_time='2025-12-01 00:00:00',
    end_time='2025-12-01 23:59:59',
    debug=True
)

print(f"获取: {result.fetched}, 保存: {result.saved}")
```

```bash
# 命令行使用
python run.py pull -c wdt -s trade --start 2025-12-01 --debug
python run.py list
```

