# -*- coding: utf-8 -*-
"""OperantID Agent 封装：配置读取、帐号解析、可选依赖。"""

import os
from typing import Any, Dict, List, Optional

from core.config import get_config


def load_operant_config() -> Dict[str, Any]:
    cfg = get_config()
    raw = cfg.get('operantid')
    if not isinstance(raw, dict):
        raw = {}
    accounts = raw.get('accounts') or []
    if not isinstance(accounts, list):
        accounts = []
    out = {
        'enabled': raw.get('enabled', True),
        'provider': raw.get('provider') or os.getenv('OPERANTID_PROVIDER') or 'gemini',
        'model': raw.get('model') or os.getenv('OPERANTID_MODEL') or 'gemini-2.0-flash',
        'api_key': raw.get('api_key') or os.getenv('OPERANTID_API_KEY') or os.getenv('GOOGLE_API_KEY') or '',
        'base_url': raw.get('base_url') or os.getenv('OPERANTID_BASE_URL') or '',
        'headless': bool(raw.get('headless', True)),
        'max_steps': int(raw.get('max_steps') or 40),
        'download_dir': raw.get('download_dir') or os.path.join('web', 'data', 'operant_downloads'),
        'accounts': accounts,
        'browser_config': raw.get('browser_config') if isinstance(raw.get('browser_config'), dict) else {},
    }
    # DeepSeek / OpenRouter / Ollama 走 OpenAI 兼容协议，不能用 gemini
    base = (out['base_url'] or '').lower()
    if any(x in base for x in ('deepseek.com', 'openrouter.ai', 'localhost:11434', 'ollama')):
        out['provider'] = 'openai'
        if 'deepseek.com' in base and str(out['model']).startswith('gemini'):
            out['model'] = 'deepseek-chat'
    return out


def list_accounts(include_secrets: bool = False) -> List[Dict[str, Any]]:
    out = []
    for item in load_operant_config().get('accounts') or []:
        if not isinstance(item, dict) or not item.get('name'):
            continue
        row = {
            'name': str(item.get('name')),
            'label': item.get('label') or item.get('name'),
            'login_url': item.get('login_url') or '',
            'has_password': bool(item.get('password') or item.get('email')),
        }
        if include_secrets:
            row['email'] = item.get('email') or item.get('username') or ''
            row['password'] = item.get('password') or ''
        out.append(row)
    return out


def get_account(name: str) -> Optional[Dict[str, Any]]:
    if not name:
        return None
    for item in list_accounts(include_secrets=True):
        if item['name'] == name:
            return item
    return None


def require_operantid():
    try:
        from operantid import Agent  # type: ignore
        return Agent
    except ImportError as e:
        raise RuntimeError(
            '未安装 OperantID。请先执行: pip install operantid && playwright install chromium'
        ) from e
