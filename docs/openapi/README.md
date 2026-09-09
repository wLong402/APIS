# OpenAPI 导入包（兼容版）

若平台提示「无法解析文件，请上传有效的OpenApi3.0文件」，请按下面顺序试。

## 先测平台能不能解析

按顺序上传这几个**最小文件**：

1. [`smoke-openapi3-ascii.json`](./smoke-openapi3-ascii.json) — 最简 OpenAPI 3.0.0（推荐先测）
2. [`smoke-openapi3.json`](./smoke-openapi3.json) — 带微伴真实 path 的样例
3. [`apis/weiban__access_token.json`](./apis/weiban__access_token.json) — 单业务接口
4. [`swagger2/weiban__access_token.json`](./swagger2/weiban__access_token.json) — 若平台实际认的是 Swagger 2.0

- 若 **1 都失败**：平台「导入」可能不是标准 OpenAPI，或只支持特定模板；需要向平台方确认支持的规范（OpenAPI3 JSON / YAML / Swagger2）和样例文件。
- 若 **1 成功、业务文件失败**：把失败文件名发我，再针对性精简字段。
- 若 **OpenAPI3 失败、Swagger2 成功**：后续统一用 `swagger2/` 目录。

## 目录

| 目录 | 格式 | 说明 |
|------|------|------|
| `apis/*.json` | OpenAPI 3.0.0 | 单接口，共 32 个（推荐） |
| `bundles/*.json` | OpenAPI 3.0.0 | 按系统汇总 5 个 |
| `swagger2/*.json` | Swagger 2.0 | 备选 |

## 本版兼容改动

相对第一版 YAML，已做：

- 改为 **JSON**（不再用 YAML）
- `openapi` 固定 `"3.0.0"`
- 去掉全部 `x-*` 扩展
- path 不含 `.`（method 用下划线）
- 标题/描述改为英文 ASCII
- 统一 LF 换行、无 BOM
- Body 用 `application/json`

## 重新生成

```bash
python scripts/generate_openapi.py
```

## 导入后核对

- 源接口地址改回真实上游（奇门 / 慧经营网关、微伴、微信等）
- 奇门/慧经营真实 HTTP path 为 `/router/qm`，靠 query `method` 区分
- 认证方式：旺店通自定义签名；微伴/微信为 token
