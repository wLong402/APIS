# 如何添加新的连接器

本文档说明如何为新的外部系统添加连接器。

## 步骤概览

1. 创建目录结构
2. 实现 API 客户端
3. 实现数据仓库
4. 实现业务服务
5. 注册连接器
6. 添加配置

## 详细步骤

### 1. 创建目录结构

```bash
mkdir -p connectors/新系统名/{models,services,repositories}
```

例如添加简道云（jdy）：

```bash
mkdir -p connectors/jdy/{models,services,repositories}
```

### 2. 实现 API 客户端

```python
# connectors/jdy/client.py
from common.base_client import BaseAPIClient

class JdyClient(BaseAPIClient):
    """简道云 API 客户端"""
    
    SYSTEM_NAME = 'jdy'
    
    def __init__(self, config=None):
        super().__init__(config)
        self.api_key = self.config.get('api_key')
        self.base_url = self.config.get('base_url')
    
    def call(self, method, params, **kwargs):
        """调用简道云 API"""
        # 实现具体的 API 调用逻辑
        pass
```

### 3. 实现数据仓库

```python
# connectors/jdy/repositories/form_repo.py
from common.base_repository import BaseRepository

class FormRepository(BaseRepository):
    """表单数据仓库"""
    
    TABLE_NAME = 'form_data'
    UNIQUE_KEY = 'data_id'
    SYSTEM_PREFIX = 'jdy'  # 表名前缀
```

### 4. 实现业务服务

```python
# connectors/jdy/services/form_service.py
from common.base_service import BasePullService, PullResult

class FormPullService(BasePullService):
    """表单数据拉取服务"""
    
    SERVICE_NAME = 'form'
    SYSTEM_NAME = 'jdy'
    
    def pull(self, start_time, end_time, **kwargs):
        # 实现拉取逻辑
        data = self.client.get_form_data(...)
        saved = self.repo.save_batch(data)
        return PullResult(fetched=len(data), saved=saved)
```

### 5. 注册连接器

```python
# connectors/jdy/__init__.py
from .client import JdyClient
from .services import FormPullService
from .repositories import FormRepository

CONNECTOR_INFO = {
    'name': 'jdy',
    'display_name': '简道云',
    'version': '1.0.0',
    'services': {
        'form': {
            'name': '表单数据',
            'class': FormPullService,
        },
    },
}
```

然后在 `connectors/__init__.py` 中添加：

```python
try:
    from .jdy import CONNECTOR_INFO as JDY_INFO
    register_connector('jdy', JDY_INFO)
except ImportError:
    pass
```

### 6. 添加配置

在 `config/config.yaml` 中添加：

```yaml
connectors:
  jdy:
    enabled: true
    api_key: "your-api-key"
    base_url: "https://api.jiandaoyun.com"
```

## 测试

```bash
# 列出连接器，确认新连接器已注册
python run.py list

# 测试拉取
python run.py pull -c jdy -s form --start 2025-12-01
```

