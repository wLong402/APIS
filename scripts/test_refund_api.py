#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

import json
import time
import hashlib
import requests
from urllib.parse import urlencode
from connectors.wdt.sdk.sign import WdtSignUtil

def generate_sign(params, secret):
    sign_str = WdtSignUtil.build_sign_string(params)
    full_str = secret + sign_str + secret
    print(f"签名字符串: {sign_str}")
    print(f"完整签名串: {full_str}")
    return hashlib.md5(full_str.encode('utf-8')).hexdigest()

def test_with_official_params():
    gateway = 'http://47.92.239.46/openapi'
    secret = ''  # 需要填入测试账号的secret
    
    params_json = json.dumps([{"modified_from": "2020-01-01 00:00:00", "modified_to": "2020-01-20 00:00:00"}], ensure_ascii=False)
    timestamp = int(time.time()) - 1325347200
    
    sign_params = {
        'method': 'aftersales.refund.Refund.search',
        'v': '1.0',
        'timestamp': str(timestamp),
        'sid': 'wdtapi3',
        'key': 'wdtapi3-test2',
        'salt': '1566006427136280c53ba-14aa-48dd-a36e-1c2dbfb3a17c',
        'params': params_json,
        'page_size': '10',
        'page_no': '0',
        'calc_total': '1',
    }
    
    sign = generate_sign(sign_params, secret)
    
    url_params = {
        'method': 'aftersales.refund.Refund.search',
        'v': '1.0',
        'timestamp': str(timestamp),
        'sid': 'wdtapi3',
        'key': 'wdtapi3-test2',
        'salt': '1566006427136280c53ba-14aa-48dd-a36e-1c2dbfb3a17c',
        'sign': sign,
        'page_size': '10',
        'page_no': '0',
        'calc_total': '1',
    }
    
    url = f"{gateway}?{urlencode(url_params)}"
    body = {'params': params_json}
    
    print(f"URL: {url}")
    print(f"Body: {body}")
    
    resp = requests.post(url, data=body, headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
    print(f"Response: {resp.text}")

def test_with_your_params():
    gateway = 'http://wdt.wangdian.cn/openapi'
    secret = '168b0a063de6a1791c1107d9794c1511'
    
    params_json = json.dumps([{"modified_from": "2025-12-01 20:00:00", "modified_to": "2025-12-01 20:59:59"}], ensure_ascii=False)
    timestamp = int(time.time()) - 1325347200
    
    sign_params = {
        'method': 'aftersales.refund.Refund.search',
        'v': '1.0',
        'timestamp': str(timestamp),
        'sid': 'lqx3',
        'key': '33457302',
        'salt': '152112177237114209c96f4a83c35fec',
        'params': params_json,
        'page_size': '200',
        'page_no': '0',
        'calc_total': '1',
    }
    
    sign = generate_sign(sign_params, secret)
    
    url_params = {
        'method': 'aftersales.refund.Refund.search',
        'v': '1.0',
        'timestamp': str(timestamp),
        'sid': 'lqx3',
        'key': '33457302',
        'salt': '152112177237114209c96f4a83c35fec',
        'sign': sign,
        'page_size': '200',
        'page_no': '0',
        'calc_total': '1',
    }
    
    url = f"{gateway}?{urlencode(url_params)}"
    body = {'params': params_json}
    
    print(f"URL: {url}")
    print(f"Body: {body}")
    
    resp = requests.post(url, data=body, headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
    print(f"Response: {resp.text}")

if __name__ == '__main__':
    print("=== 测试你的账号 ===")
    test_with_your_params()
