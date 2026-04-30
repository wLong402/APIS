#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
签名工具模块
实现旺店通签名和淘宝奇门签名算法
"""

import hashlib
import json
from typing import Dict, Any, List, Union


class WdtSignUtil:
    """旺店通签名工具类"""
    
    # 签名时排除的字段
    EXCLUDE_FIELDS = ['wdt3_customer_id', 'wdt_sign']
    
    @staticmethod
    def is_json(value: Any) -> bool:
        """
        判断是否为JSON字符串（首字符短路，避免对普通字符串解析）
        """
        if not isinstance(value, str) or len(value) < 2:
            return False
        first = value[0]
        if first != '{' and first != '[':
            return False
        try:
            json.loads(value)
            return True
        except (json.JSONDecodeError, TypeError, ValueError):
            return False
    
    @classmethod
    def build_sign_string(cls, data: Any) -> str:
        """
        递归构建签名字符串
        
        将嵌套的字典/列表结构展开为排序后的字符串
        
        Args:
            data: 待处理的数据（字典、列表或基本类型）
            
        Returns:
            签名字符串
        """
        sign_str = ''
        
        if isinstance(data, dict):
            # 字典按key排序后拼接
            for key in sorted(data.keys()):
                if key in cls.EXCLUDE_FIELDS:
                    continue
                
                sign_str += key
                value = data[key]
                
                if isinstance(value, dict):
                    sign_str += cls.build_sign_string(value)
                elif isinstance(value, list):
                    sign_str += ''.join(cls.build_sign_string(item) for item in value)
                elif isinstance(value, bool):
                    sign_str += 'true' if value else 'false'
                elif cls.is_json(value):
                    # JSON字符串需要解析后递归处理
                    sign_str += cls.build_sign_string(json.loads(value))
                else:
                    sign_str += str(value)
                    
        elif isinstance(data, list):
            sign_str += ''.join(cls.build_sign_string(item) for item in data)
        else:
            sign_str += str(data)
        
        return sign_str
    
    @staticmethod
    def remove_method_prefix(method: str) -> str:
        """
        处理方法名（保持wdt.开头）
        
        Args:
            method: API方法名
            
        Returns:
            处理后的方法名
        """
        if method.startswith('wdt.'):
            return method
        return method.split('.', 1)[1] if '.' in method else method
    
    @classmethod
    def generate_wdt_sign(cls, api_params: Dict, method_name: str, secret: str) -> str:
        """
        生成旺店通签名
        
        签名规则：MD5(secret + 排序拼接字符串 + secret)
        
        Args:
            api_params: API参数字典
            method_name: API方法名
            secret: 旺店通密钥
            
        Returns:
            签名字符串（MD5小写）
        """
        sign_params = api_params.copy()
        sign_params['method'] = cls.remove_method_prefix(method_name)
        sign_str = cls.build_sign_string(sign_params)
        
        full_str = secret + sign_str + secret
        return hashlib.md5(full_str.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_top_sign(params: Dict, secret: str) -> str:
        """
        生成淘宝奇门签名
        
        签名规则：MD5(secret + key1value1key2value2... + secret).upper()
        
        Args:
            params: 参数字典（包含系统参数和业务参数）
            secret: 淘宝应用密钥
            
        Returns:
            签名字符串（MD5大写）
        """
        # 过滤掉字典类型和@开头的文件参数
        sorted_params = sorted(
            [(k, v) for k, v in params.items() 
             if not isinstance(v, dict) and not (isinstance(v, str) and v.startswith('@'))],
            key=lambda x: x[0]
        )
        
        sign_str = secret + ''.join(f"{k}{v}" for k, v in sorted_params) + secret
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()

