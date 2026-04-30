# -*- coding: utf-8 -*-
"""
微伴连接器

用于对接微伴助手 API
"""

from .client import WeibanClient, get_weiban_client
from .services import ExternalUserPullService, ExternalUserDetailPullService
from .repositories import ExternalUserRepository, FollowStaffRepository

# 连接器信息（用于自动注册）
CONNECTOR_INFO = {
    'name': 'weiban',
    'display_name': '微伴助手',
    'description': '微伴助手 API 连接器',
    'version': '1.0.0',
    'client_class': WeibanClient,
    'services': {
        'external_user': {
            'class': ExternalUserPullService,
            'description': '客户列表拉取',
        },
        'external_user_detail': {
            'class': ExternalUserDetailPullService,
            'description': '客户详情拉取（follow_staffs）',
        },
    },
}

__all__ = [
    'WeibanClient',
    'get_weiban_client',
    'CONNECTOR_INFO',
    'ExternalUserPullService',
    'ExternalUserDetailPullService',
    'ExternalUserRepository',
    'FollowStaffRepository',
]

