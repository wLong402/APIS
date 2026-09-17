# OpenAPI 导入包（兼容版）

若平台提示「无法解析文件，请上传有效的OpenApi3.0文件」，请优先使用本目录下的 **JSON** 文件。

## 推荐导入顺序

1. `apis/*.json` — OpenAPI **3.0.0** 单接口（最推荐）
2. `bundles/*.json` — 按系统汇总的 OpenAPI 3.0.0
3. `swagger2/*.json` — Swagger **2.0**（平台只认 swagger 时用）

## 兼容性改动说明

- 输出 JSON，不再默认用 YAML
- `openapi` 固定为 `"3.0.0"`
- 去掉全部 `x-*` 扩展
- path 中不含 `.`（method 名改下划线）
- Body 统一 `application/json`（避免 form-urlencoded 解析失败）

## 导入后请核对

- 源接口地址应改回真实上游网关（见下方清单）
- 奇门/慧经营真实 path 为 `/router/qm`，靠 query `method` 区分
- 认证：旺店通自定义签名；微伴/微信为 token

## 重新生成

```bash
python scripts/generate_openapi.py
```

## 接口清单（共 33）

### wdt-qimen

| 服务 | 标题 | OpenAPI3 文件 | 上游 |
|------|------|---------------|------|
| `trade` | rawtrade search | `apis/wdt-qimen__trade.json` | `http://3ldsmu02o9.api.taobao.com` |
| `erp_trade` | erp trade query with detail | `apis/wdt-qimen__erp_trade.json` | `http://3ldsmu02o9.api.taobao.com` |
| `history_trade` | history trade query with detail | `apis/wdt-qimen__history_trade.json` | `http://3ldsmu02o9.api.taobao.com` |
| `refund` | raw refund search | `apis/wdt-qimen__refund.json` | `http://3ldsmu02o9.api.taobao.com` |
| `aftersales_refund` | aftersales refund search | `apis/wdt-qimen__aftersales_refund.json` | `http://3ldsmu02o9.api.taobao.com` |
| `stockout_sales_query_with_detail` | stockout sales query with detail | `apis/wdt-qimen__stockout_sales_query_with_detail.json` | `http://3ldsmu02o9.api.taobao.com` |
| `stockout_other_query_with_detail` | stockout other query with detail | `apis/wdt-qimen__stockout_other_query_with_detail.json` | `http://3ldsmu02o9.api.taobao.com` |
| `stockin_refund_query_with_detail` | stockin refund query with detail | `apis/wdt-qimen__stockin_refund_query_with_detail.json` | `http://3ldsmu02o9.api.taobao.com` |
| `stockspec` | stockspec search | `apis/wdt-qimen__stockspec.json` | `http://3ldsmu02o9.api.taobao.com` |

### wdt-hjy

| 服务 | 标题 | OpenAPI3 文件 | 上游 |
|------|------|---------------|------|
| `bill_standard` | bill standard query | `apis/wdt-hjy__bill_standard.json` | `http://332wh0cyoi.api.taobao.com` |
| `bk_share_data` | bk share datas query | `apis/wdt-hjy__bk_share_data.json` | `http://332wh0cyoi.api.taobao.com` |
| `fixbill_data_summary` | fixbill datas summary query | `apis/wdt-hjy__fixbill_data_summary.json` | `http://332wh0cyoi.api.taobao.com` |
| `marketing_detail` | marketing detail query | `apis/wdt-hjy__marketing_detail.json` | `http://332wh0cyoi.api.taobao.com` |
| `marketing_share_result` | marketing share result | `apis/wdt-hjy__marketing_share_result.json` | `http://332wh0cyoi.api.taobao.com` |
| `expense_sku_day_summary` | expense sku day summary | `apis/wdt-hjy__expense_sku_day_summary.json` | `http://332wh0cyoi.api.taobao.com` |
| `expense_sku_share_day_detail` | expense sku share day detail | `apis/wdt-hjy__expense_sku_share_day_detail.json` | `http://332wh0cyoi.api.taobao.com` |
| `profits_sku` | profits sku query | `apis/wdt-hjy__profits_sku.json` | `http://332wh0cyoi.api.taobao.com` |
| `profits_order` | profits order query | `apis/wdt-hjy__profits_order.json` | `http://332wh0cyoi.api.taobao.com` |
| `profits_live_sku` | profits live sku query | `apis/wdt-hjy__profits_live_sku.json` | `http://332wh0cyoi.api.taobao.com` |
| `profits_live_order` | profits live order query | `apis/wdt-hjy__profits_live_order.json` | `http://332wh0cyoi.api.taobao.com` |
| `profits_live_refund` | profits live refund query | `apis/wdt-hjy__profits_live_refund.json` | `http://332wh0cyoi.api.taobao.com` |
| `sht_recon_detail` | sht recon detail query | `apis/wdt-hjy__sht_recon_detail.json` | `http://332wh0cyoi.api.taobao.com` |
| `recon_delivery_detail` | recon delivery details query | `apis/wdt-hjy__recon_delivery_detail.json` | `http://332wh0cyoi.api.taobao.com` |
| `recon_order_confirm_summary` | recon order confirm summary | `apis/wdt-hjy__recon_order_confirm_summary.json` | `http://332wh0cyoi.api.taobao.com` |
| `recon_dztk_summary` | recon dztk summary query | `apis/wdt-hjy__recon_dztk_summary.json` | `http://332wh0cyoi.api.taobao.com` |

### wdt-openapi

| 服务 | 标题 | OpenAPI3 文件 | 上游 |
|------|------|---------------|------|
| `warehouse` | query warehouse | `apis/wdt-openapi__warehouse.json` | `http://wdt.wangdian.cn` |
| `logistics_trace` | search logistics trace | `apis/wdt-openapi__logistics_trace.json` | `http://wdt.wangdian.cn` |
| `trade_query_with_detail` | sales trade query with detail | `apis/wdt-openapi__trade_query_with_detail.json` | `http://wdt.wangdian.cn` |

### weiban

| 服务 | 标题 | OpenAPI3 文件 | 上游 |
|------|------|---------------|------|
| `access_token` | get access token | `apis/weiban__access_token.json` | `https://open.weibanzhushou.com` |
| `external_user` | external user staff relation list | `apis/weiban__external_user.json` | `https://open.weibanzhushou.com` |
| `external_user_detail` | external user batch get | `apis/weiban__external_user_detail.json` | `https://open.weibanzhushou.com` |

### wechat-store

| 服务 | 标题 | OpenAPI3 文件 | 上游 |
|------|------|---------------|------|
| `stable_token` | get stable token | `apis/wechat-store__stable_token.json` | `https://api.weixin.qq.com` |
| `order_get` | get order | `apis/wechat-store__order_get.json` | `https://api.weixin.qq.com` |
