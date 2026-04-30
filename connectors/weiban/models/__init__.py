# -*- coding: utf-8 -*-
"""
微伴数据模型
"""

from enum import IntEnum


class ExternalUserType(IntEnum):
    """外部联系人类型"""
    WECHAT = 1        # 微信用户
    WORK_WECHAT = 2   # 企业微信用户


class Gender(IntEnum):
    """性别"""
    UNKNOWN = 0   # 未知
    MALE = 1      # 男
    FEMALE = 2    # 女


class OutflowStatus(IntEnum):
    """流失状态"""
    NOT_OUTFLOW = 0  # 未流失
    OUTFLOW = 1      # 已流失


__all__ = [
    'ExternalUserType',
    'Gender',
    'OutflowStatus',
]

