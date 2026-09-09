#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量生成数据平台导入用 OpenAPI / Swagger 文件（兼容版）。

针对平台报错「无法解析文件，请上传有效的OpenApi3.0文件」做了兼容处理：
  - 主推 JSON（多数中文平台对 JSON 比 YAML 更稳）
  - openapi 版本固定为 "3.0.0"
  - 去掉全部 x-* 扩展字段
  - path 不含点号（改用下划线）
  - 去掉空 parameters、复杂 multiline、form-urlencoded（改用 JSON body）
  - 同时输出 Swagger 2.0，作为备选导入格式

输出：
  docs/openapi/apis/*.json          # 单接口 OpenAPI 3.0.0（推荐）
  docs/openapi/bundles/*.json       # 按系统汇总 OpenAPI 3.0.0
  docs/openapi/swagger2/*.json      # 单接口 Swagger 2.0（备选）
  docs/openapi/README.md

用法：
  python scripts/generate_openapi.py
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "docs" / "openapi"
OUT_APIS = OUT_ROOT / "apis"
OUT_BUNDLES = OUT_ROOT / "bundles"
OUT_SWAGGER2 = OUT_ROOT / "swagger2"
OUT_README = OUT_ROOT / "README.md"

QIMEN_HOST = "3ldsmu02o9.api.taobao.com"
QIMEN_BASE = f"http://{QIMEN_HOST}"
HJY_HOST = "332wh0cyoi.api.taobao.com"
HJY_BASE = f"http://{HJY_HOST}"
OPENAPI_HOST = "wdt.wangdian.cn"
OPENAPI_BASE = f"http://{OPENAPI_HOST}"
WEIBAN_HOST = "open.weibanzhushou.com"
WEIBAN_BASE = f"https://{WEIBAN_HOST}"
WECHAT_HOST = "api.weixin.qq.com"
WECHAT_BASE = f"https://{WECHAT_HOST}"


def _slug(s: str) -> str:
    s = s.replace(".", "_")
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", s).strip("_").lower()


def _safe_path(*parts: str) -> str:
    """OpenAPI path：仅字母数字下划线斜杠，不含点号。"""
    cleaned = ["/".join(_slug(p) for p in parts if p)]
    return "/" + cleaned[0]


APIS: List[Dict[str, Any]] = []


def _ok_response() -> Dict[str, Any]:
    return {
        "200": {
            "description": "OK",
            "content": {
                "application/json": {
                    "schema": {"type": "object"}
                }
            },
        }
    }


def _json_body(properties: Dict[str, Any], required: Optional[List[str]] = None) -> Dict[str, Any]:
    schema: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": schema
            }
        },
    }


def add_api(
    *,
    group: str,
    group_title: str,
    service: str,
    title: str,
    method_name: str,
    server: str,
    host: str,
    scheme: str,
    path: str,
    http_method: str,
    parameters: Optional[List[Dict[str, Any]]] = None,
    request_body: Optional[Dict[str, Any]] = None,
    description: str = "",
) -> None:
    op: Dict[str, Any] = {
        "operationId": _slug(f"{group}_{service}"),
        "summary": title,
        "description": description or f"{group_title} - {title} ({method_name})",
        "tags": [group_title],
        "responses": _ok_response(),
    }
    if parameters:
        op["parameters"] = parameters
    if request_body:
        op["requestBody"] = request_body

    APIS.append(
        {
            "group": group,
            "group_title": group_title,
            "service": service,
            "title": title,
            "method_name": method_name,
            "server": server,
            "host": host,
            "scheme": scheme,
            "http_method": http_method.lower(),
            "path": path,
            "operation": op,
        }
    )


def _qimen_query_params(method: str) -> List[Dict[str, Any]]:
    return [
        {"name": "app_key", "in": "query", "required": True, "schema": {"type": "string"}},
        {"name": "v", "in": "query", "required": True, "schema": {"type": "string"}, "example": "2.0"},
        {"name": "format", "in": "query", "required": True, "schema": {"type": "string"}, "example": "json"},
        {"name": "sign_method", "in": "query", "required": True, "schema": {"type": "string"}, "example": "md5"},
        {"name": "method", "in": "query", "required": True, "schema": {"type": "string"}, "example": method},
        {"name": "timestamp", "in": "query", "required": True, "schema": {"type": "string"}},
        {"name": "target_app_key", "in": "query", "required": True, "schema": {"type": "string"}},
        {"name": "session", "in": "query", "required": False, "schema": {"type": "string"}},
        {"name": "sign", "in": "query", "required": True, "schema": {"type": "string"}},
    ]


_QIMEN_BODY_PROPS = {
    "params": {"type": "string", "description": "business params JSON string"},
    "pager": {"type": "string", "description": "pager JSON string"},
    "datetime": {"type": "string"},
    "wdt_appkey": {"type": "string"},
    "wdt_salt": {"type": "string"},
    "wdt3_customer_id": {"type": "string"},
    "wdt_sign": {"type": "string"},
}

_HJY_BODY_PROPS = {
    "appId": {"type": "string"},
    "sid": {"type": "string"},
    "hjySign": {"type": "string"},
    "startDate": {"type": "string"},
    "endDate": {"type": "string"},
    "nextRequestId": {"type": "string"},
}


def _register_all() -> None:
    qimen_items = [
        ("trade", "rawtrade search", "wdt.sales.rawtrade.search"),
        ("erp_trade", "erp trade query with detail", "wdt.sales.tradequery.querywithdetail"),
        ("history_trade", "history trade query with detail", "wdt.sales.tradequery.queryhistorywithdetail"),
        ("refund", "raw refund search", "wdt.aftersales.refund.rawrefund.search"),
        ("aftersales_refund", "aftersales refund search", "wdt.aftersales.refund.refund.search"),
        ("stockout_sales_query_with_detail", "stockout sales query with detail", "wdt.wms.stockout.sales.querywithdetail"),
        ("stockout_other_query_with_detail", "stockout other query with detail", "wdt.wms.stockout.other.querywithdetail"),
        ("stockin_refund_query_with_detail", "stockin refund query with detail", "wdt.wms.stockin.refund.querywithdetail"),
        ("stockspec", "stockspec search", "wdt.wms.stockspec.search"),
    ]
    for service, title, method in qimen_items:
        add_api(
            group="wdt-qimen",
            group_title="wdt-qimen",
            service=service,
            title=title,
            method_name=method,
            server=QIMEN_BASE,
            host=QIMEN_HOST,
            scheme="http",
            path=_safe_path("router", "qm", method),
            http_method="post",
            parameters=_qimen_query_params(method),
            request_body=_json_body(_QIMEN_BODY_PROPS, ["params", "pager", "wdt_sign"]),
            description=f"WDT Qimen API method={method}. Real upstream: {QIMEN_BASE}/router/qm",
        )

    hjy_items = [
        ("bill_standard", "bill standard query", "wdt.hjy.bill.billsatndard.query"),
        ("bk_share_data", "bk share datas query", "wdt.hjy.bk.share.datas.query"),
        ("fixbill_data_summary", "fixbill datas summary query", "wdt.hjy.fixbill.datas.summary.query"),
        ("marketing_detail", "marketing detail query", "wdt.hjy.bill.marketing.detail.query"),
        ("marketing_share_result", "marketing share result", "wdt.hjy.bill.ext.marketing.share.result"),
        ("expense_sku_day_summary", "expense sku day summary", "wdt.hjy.expense.sku.day.summary.main.query"),
        ("expense_sku_share_day_detail", "expense sku share day detail", "wdt.hjy.expense.sku.share.day.detail.query"),
        ("profits_sku", "profits sku query", "wdt.hjy.ba.profits.sku.query"),
        ("profits_order", "profits order query", "wdt.hjy.bac.profits.order.query"),
        ("profits_live_sku", "profits live sku query", "wdt.hjy.ba.profits.live.sku.query"),
        ("profits_live_order", "profits live order query", "wdt.hjy.ba.profits.live.order.query"),
        ("profits_live_refund", "profits live refund query", "wdt.hjy.bac.profits.live.re.order.query"),
        ("sht_recon_detail", "sht recon detail query", "wdt.hjy.recon.shtrecondetail.query"),
        ("recon_delivery_detail", "recon delivery details query", "wdt.hjy.recon.delivery.details.query"),
        ("recon_order_confirm_summary", "recon order confirm summary", "wdt.hjy.recon.order.confirm.summary.query"),
        ("recon_dztk_summary", "recon dztk summary query", "wdt.hjy.recon.dztk.summary.query"),
    ]
    for service, title, method in hjy_items:
        props = dict(_HJY_BODY_PROPS)
        if service == "bill_standard":
            props["businesstime"] = {"type": "string"}
            props["shopNo"] = {"type": "string"}
        add_api(
            group="wdt-hjy",
            group_title="wdt-hjy",
            service=service,
            title=title,
            method_name=method,
            server=HJY_BASE,
            host=HJY_HOST,
            scheme="http",
            path=_safe_path("router", "qm", method),
            http_method="post",
            parameters=_qimen_query_params(method),
            request_body=_json_body(props, ["appId", "sid", "hjySign"]),
            description=f"HJY API method={method}. Real upstream: {HJY_BASE}/router/qm",
        )

    openapi_items = [
        ("warehouse", "query warehouse", "setting.Warehouse.queryWarehouse"),
        ("logistics_trace", "search logistics trace", "statistic.GoodsSendStatistic.searchLogisticsTrace"),
    ]
    for service, title, method in openapi_items:
        add_api(
            group="wdt-openapi",
            group_title="wdt-openapi",
            service=service,
            title=title,
            method_name=method,
            server=OPENAPI_BASE,
            host=OPENAPI_HOST,
            scheme="http",
            path=_safe_path("openapi", method),
            http_method="post",
            parameters=[
                {"name": "method", "in": "query", "required": True, "schema": {"type": "string"}, "example": method},
                {"name": "v", "in": "query", "required": True, "schema": {"type": "string"}, "example": "1.0"},
                {"name": "timestamp", "in": "query", "required": True, "schema": {"type": "string"}},
                {"name": "sid", "in": "query", "required": True, "schema": {"type": "string"}},
                {"name": "key", "in": "query", "required": True, "schema": {"type": "string"}},
                {"name": "salt", "in": "query", "required": True, "schema": {"type": "string"}},
                {"name": "sign", "in": "query", "required": True, "schema": {"type": "string"}},
                {"name": "page_size", "in": "query", "required": False, "schema": {"type": "string"}},
                {"name": "page_no", "in": "query", "required": False, "schema": {"type": "string"}},
            ],
            request_body={
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "array",
                            "items": {"type": "object"},
                        }
                    }
                },
            },
            description=f"WDT OpenAPI method={method}. Real upstream: {OPENAPI_BASE}/openapi",
        )

    add_api(
        group="weiban",
        group_title="weiban",
        service="access_token",
        title="get access token",
        method_name="access_token_get",
        server=WEIBAN_BASE,
        host=WEIBAN_HOST,
        scheme="https",
        path="/open-api/access_token/get",
        http_method="post",
        request_body=_json_body(
            {"corp_id": {"type": "string"}, "secret": {"type": "string"}},
            ["corp_id", "secret"],
        ),
    )
    add_api(
        group="weiban",
        group_title="weiban",
        service="external_user",
        title="external user staff relation list",
        method_name="external_user_staff_relation_list",
        server=WEIBAN_BASE,
        host=WEIBAN_HOST,
        scheme="https",
        path="/open-api/external_user_staff_relation/list",
        http_method="get",
        parameters=[
            {"name": "access_token", "in": "query", "required": True, "schema": {"type": "string"}},
            {"name": "staff_id", "in": "query", "required": False, "schema": {"type": "string"}},
            {"name": "offset", "in": "query", "required": False, "schema": {"type": "integer"}},
            {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer"}},
        ],
    )
    add_api(
        group="weiban",
        group_title="weiban",
        service="external_user_detail",
        title="external user batch get",
        method_name="external_user_batch_get",
        server=WEIBAN_BASE,
        host=WEIBAN_HOST,
        scheme="https",
        path="/open-api/external_user/batch_get",
        http_method="post",
        parameters=[
            {"name": "access_token", "in": "query", "required": True, "schema": {"type": "string"}},
        ],
        request_body=_json_body(
            {"external_user_ids": {"type": "array", "items": {"type": "string"}}},
        ),
    )

    add_api(
        group="wechat-store",
        group_title="wechat-store",
        service="stable_token",
        title="get stable token",
        method_name="stable_token",
        server=WECHAT_BASE,
        host=WECHAT_HOST,
        scheme="https",
        path="/cgi-bin/stable_token",
        http_method="post",
        request_body=_json_body(
            {
                "grant_type": {"type": "string", "example": "client_credential"},
                "appid": {"type": "string"},
                "secret": {"type": "string"},
            },
            ["grant_type", "appid", "secret"],
        ),
    )
    add_api(
        group="wechat-store",
        group_title="wechat-store",
        service="order_get",
        title="get order",
        method_name="order_get",
        server=WECHAT_BASE,
        host=WECHAT_HOST,
        scheme="https",
        path="/channels/ec/order/get",
        http_method="post",
        parameters=[
            {"name": "access_token", "in": "query", "required": True, "schema": {"type": "string"}},
        ],
        request_body=_json_body({"order_id": {"type": "string"}}, ["order_id"]),
    )


def build_openapi3(api: Dict[str, Any]) -> Dict[str, Any]:
    """严格兼容的 OpenAPI 3.0.0（无 x-*）。"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": api["title"],
            "description": api["operation"]["description"],
            "version": "1.0.0",
        },
        "servers": [
            {"url": api["server"]}
        ],
        "tags": [{"name": api["group_title"]}],
        "paths": {
            api["path"]: {
                api["http_method"]: api["operation"],
            }
        },
    }


def build_openapi3_bundle(group: str, group_title: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    paths: Dict[str, Any] = {}
    for api in items:
        paths.setdefault(api["path"], {})[api["http_method"]] = api["operation"]
    return {
        "openapi": "3.0.0",
        "info": {
            "title": f"{group_title}",
            "description": f"{group_title} APIs, count={len(items)}",
            "version": "1.0.0",
        },
        "servers": [{"url": items[0]["server"]}],
        "tags": [{"name": group_title}],
        "paths": paths,
    }


def _swagger2_param(p: Dict[str, Any]) -> Dict[str, Any]:
    schema = p.get("schema") or {"type": "string"}
    out: Dict[str, Any] = {
        "name": p["name"],
        "in": p["in"],
        "required": bool(p.get("required", False)),
        "type": schema.get("type", "string"),
    }
    if "example" in p:
        out["x-example"] = p["example"]  # may be stripped by some tools; keep minimal
    if "description" in p:
        out["description"] = p["description"]
    # Swagger2 does not love x-example; remove for max compatibility
    out.pop("x-example", None)
    return out


def build_swagger2(api: Dict[str, Any]) -> Dict[str, Any]:
    """Swagger 2.0 备选（部分平台只认 swagger）。"""
    op = api["operation"]
    sw_op: Dict[str, Any] = {
        "operationId": op["operationId"],
        "summary": op["summary"],
        "description": op["description"],
        "tags": op["tags"],
        "produces": ["application/json"],
        "responses": {
            "200": {
                "description": "OK",
                "schema": {"type": "object"},
            }
        },
    }
    params: List[Dict[str, Any]] = []
    for p in op.get("parameters") or []:
        params.append(_swagger2_param(p))

    rb = op.get("requestBody")
    if rb:
        content = (rb.get("content") or {}).get("application/json") or {}
        schema = content.get("schema") or {"type": "object"}
        sw_op["consumes"] = ["application/json"]
        params.append(
            {
                "name": "body",
                "in": "body",
                "required": bool(rb.get("required", True)),
                "schema": schema,
            }
        )
    if params:
        sw_op["parameters"] = params

    return {
        "swagger": "2.0",
        "info": {
            "title": api["title"],
            "description": op["description"],
            "version": "1.0.0",
        },
        "host": api["host"],
        "basePath": "/",
        "schemes": [api["scheme"]],
        "tags": [{"name": api["group_title"]}],
        "paths": {
            api["path"]: {
                api["http_method"]: sw_op,
            }
        },
    }


def write_json(path: Path, data: Dict[str, Any], *, ascii_only: bool = False) -> None:
    """写入 JSON：UTF-8 无 BOM、LF 换行；可选 ascii_only 规避部分平台中文解析问题。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=ascii_only, indent=2) + "\n"
    # 强制 LF，避免 Windows CRLF 导致部分解析器失败
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def reset_dirs() -> None:
    for d in (OUT_APIS, OUT_BUNDLES, OUT_SWAGGER2):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    # 清理旧 YAML，避免用户误传
    for old in OUT_ROOT.rglob("*.yaml"):
        old.unlink()


def write_readme(apis: List[Dict[str, Any]]) -> None:
    by_group: Dict[str, List[Dict[str, Any]]] = {}
    for a in apis:
        by_group.setdefault(a["group"], []).append(a)

    lines = [
        "# OpenAPI 导入包（兼容版）",
        "",
        "若平台提示「无法解析文件，请上传有效的OpenApi3.0文件」，请优先使用本目录下的 **JSON** 文件。",
        "",
        "## 推荐导入顺序",
        "",
        "1. `apis/*.json` — OpenAPI **3.0.0** 单接口（最推荐）",
        "2. `bundles/*.json` — 按系统汇总的 OpenAPI 3.0.0",
        "3. `swagger2/*.json` — Swagger **2.0**（平台只认 swagger 时用）",
        "",
        "## 兼容性改动说明",
        "",
        "- 输出 JSON，不再默认用 YAML",
        "- `openapi` 固定为 `\"3.0.0\"`",
        "- 去掉全部 `x-*` 扩展",
        "- path 中不含 `.`（method 名改下划线）",
        "- Body 统一 `application/json`（避免 form-urlencoded 解析失败）",
        "",
        "## 导入后请核对",
        "",
        "- 源接口地址应改回真实上游网关（见下方清单）",
        "- 奇门/慧经营真实 path 为 `/router/qm`，靠 query `method` 区分",
        "- 认证：旺店通自定义签名；微伴/微信为 token",
        "",
        "## 重新生成",
        "",
        "```bash",
        "python scripts/generate_openapi.py",
        "```",
        "",
        f"## 接口清单（共 {len(apis)}）",
        "",
    ]
    for group, items in by_group.items():
        lines.append(f"### {items[0]['group_title']}")
        lines.append("")
        lines.append("| 服务 | 标题 | OpenAPI3 文件 | 上游 |")
        lines.append("|------|------|---------------|------|")
        for a in items:
            fname = f"{a['group']}__{_slug(a['service'])}.json"
            lines.append(
                f"| `{a['service']}` | {a['title']} | `apis/{fname}` | `{a['server']}` |"
            )
        lines.append("")

    OUT_README.write_text("\n".join(lines), encoding="utf-8")


def _minimal_smoke_file() -> None:
    """极简样例：先测平台能否解析 OpenAPI3。"""
    # 最简：几乎无业务字段
    ascii_doc = {
        "openapi": "3.0.0",
        "info": {"title": "smoke-test", "version": "1.0.0", "description": "minimal"},
        "paths": {
            "/ping": {
                "get": {
                    "summary": "ping",
                    "operationId": "ping",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }
    write_json(OUT_ROOT / "smoke-openapi3-ascii.json", ascii_doc, ascii_only=True)

    # 含真实微伴 path 的样例
    doc = {
        "openapi": "3.0.0",
        "info": {
            "title": "weiban-access-token",
            "version": "1.0.0",
            "description": "weiban access_token get",
        },
        "servers": [{"url": "https://open.weibanzhushou.com"}],
        "paths": {
            "/open-api/access_token/get": {
                "post": {
                    "summary": "get access token",
                    "operationId": "weibanAccessToken",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "corp_id": {"type": "string"},
                                        "secret": {"type": "string"},
                                    },
                                    "required": ["corp_id", "secret"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            },
                        }
                    },
                }
            }
        },
    }
    write_json(OUT_ROOT / "smoke-openapi3.json", doc, ascii_only=True)


def main() -> None:
    APIS.clear()
    _register_all()
    reset_dirs()

    by_group: Dict[str, List[Dict[str, Any]]] = {}
    for api in APIS:
        by_group.setdefault(api["group"], []).append(api)
        fname = f"{api['group']}__{_slug(api['service'])}.json"
        # ascii_only=True: 中文平台解析器对 unicode 更挑剔时更稳
        write_json(OUT_APIS / fname, build_openapi3(api), ascii_only=True)
        write_json(OUT_SWAGGER2 / fname, build_swagger2(api), ascii_only=True)

    for group, items in by_group.items():
        write_json(
            OUT_BUNDLES / f"{group}.json",
            build_openapi3_bundle(group, items[0]["group_title"], items),
            ascii_only=True,
        )

    _minimal_smoke_file()
    write_readme(APIS)

    # 快速自检
    sample = OUT_APIS / "weiban__access_token.json"
    raw = sample.read_bytes()
    assert b"\r" not in raw, "CRLF not allowed"
    data = json.loads(raw.decode("utf-8"))
    assert data["openapi"] == "3.0.0"
    assert "paths" in data and data["paths"]
    assert "x-" not in json.dumps(data)

    print(f"OK: {len(APIS)} OpenAPI3 apis -> {OUT_APIS}")
    print(f"OK: {len(by_group)} bundles -> {OUT_BUNDLES}")
    print(f"OK: {len(APIS)} swagger2 -> {OUT_SWAGGER2}")
    print("Try import in order:")
    print("  1) docs/openapi/smoke-openapi3-ascii.json")
    print("  2) docs/openapi/smoke-openapi3.json")
    print("  3) docs/openapi/apis/weiban__access_token.json")
    print("  4) docs/openapi/swagger2/weiban__access_token.json")


if __name__ == "__main__":
    main()
