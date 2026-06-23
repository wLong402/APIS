# -*- coding: utf-8 -*-
"""
统一配置管理模块

支持从 YAML 文件和环境变量加载配置，并提供配置验证
"""

import os
import yaml
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
from abc import ABC, abstractmethod

from .exceptions import ConfigError


# ============ 配置验证器 ============

class ConfigValidator(ABC):
    """配置验证器基类"""
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """
        验证配置
        
        Args:
            config: 配置字典
            
        Returns:
            错误信息列表，空列表表示验证通过
        """
        pass


class RequiredFieldsValidator(ConfigValidator):
    """必填字段验证器"""
    
    def __init__(self, required_fields: List[str], config_name: str = ''):
        self.required_fields = required_fields
        self.config_name = config_name
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        errors = []
        prefix = f"[{self.config_name}] " if self.config_name else ""
        
        for field in self.required_fields:
            if field not in config or config[field] is None or config[field] == '':
                errors.append(f"{prefix}缺少必填配置: {field}")
        
        return errors


class WdtConfigValidator(ConfigValidator):
    """旺店通配置验证器"""
    
    REQUIRED_FIELDS = [
        'app_key',
        'app_secret', 
        'qimen_appkey',
        'qimen_appsecret',
        'gateway_url',
        'target_appkey',
        'wdt3_customer_id'
    ]
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        errors = []
        
        # 检查必填字段
        for field in self.REQUIRED_FIELDS:
            if field not in config or not config[field]:
                errors.append(f"[wdt] 缺少必填配置: {field}")
        
        # 检查 app_secret 格式（应包含冒号分隔的 secret:salt）
        if 'app_secret' in config and config['app_secret']:
            if ':' not in config['app_secret']:
                errors.append("[wdt] app_secret 格式错误，应为 'secret:salt' 格式")
        
        # 检查 gateway_url 格式
        if 'gateway_url' in config and config['gateway_url']:
            url = config['gateway_url']
            if not (url.startswith('http://') or url.startswith('https://')):
                errors.append("[wdt] gateway_url 应以 http:// 或 https:// 开头")
        
        return errors


class DatabaseConfigValidator(ConfigValidator):
    """数据库配置验证器"""
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        errors = []
        
        # 检查必填字段
        required = ['host', 'user', 'database']
        for field in required:
            if field not in config or not config[field]:
                errors.append(f"[database] 缺少必填配置: {field}")
        
        # 检查端口号
        port = config.get('port', 3306)
        if not isinstance(port, int) or port <= 0 or port > 65535:
            errors.append(f"[database] port 应为有效端口号 (1-65535)，当前值: {port}")
        
        return errors


class WeibanConfigValidator(ConfigValidator):
    """微伴配置验证器"""
    
    REQUIRED_FIELDS = [
        'corp_id',
        'secret',
    ]
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        errors = []
        
        # 检查必填字段
        for field in self.REQUIRED_FIELDS:
            if field not in config or not config[field]:
                errors.append(f"[weiban] 缺少必填配置: {field}")
        
        # 检查是否为占位符
        corp_id = config.get('corp_id', '')
        secret = config.get('secret', '')
        if corp_id == 'YOUR_CORP_ID_HERE':
            errors.append("[weiban] corp_id 需要替换为真实的企业ID")
        if secret == 'YOUR_SECRET_HERE':
            errors.append("[weiban] secret 需要替换为真实的应用密钥")
        
        # 检查 base_url 格式
        if 'base_url' in config and config['base_url']:
            url = config['base_url']
            if not (url.startswith('http://') or url.startswith('https://')):
                errors.append("[weiban] base_url 应以 http:// 或 https:// 开头")
        
        return errors


# ============ 配置数据类 ============

@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = 'mysql'
    host: str = 'localhost'
    port: int = 3306
    user: str = 'root'
    password: str = ''
    database: str = 'data_sync'
    charset: str = 'utf8mb4'
    driver: str = None
    pool_size: int = 10
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'database': self.database,
            'charset': self.charset,
            'driver': self.driver,
            'pool_size': self.pool_size,
        }


@dataclass
class RedisConfig:
    """Redis配置"""
    host: str = 'localhost'
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = 'INFO'
    log_dir: str = 'logs'
    format: str = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'


@dataclass
class Config:
    """
    应用配置类
    
    统一管理所有配置项，支持从 YAML 文件加载和验证
    """
    
    # 应用配置
    app_name: str = '数据同步平台'
    env: str = 'development'
    debug: bool = True
    
    # 基础设施配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # 连接器配置（动态加载）
    connectors: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # 原始配置数据
    _raw: Dict[str, Any] = field(default_factory=dict, repr=False)
    
    # 连接器验证器注册表
    _connector_validators: Dict[str, ConfigValidator] = field(
        default_factory=lambda: {
            'wdt': WdtConfigValidator(),
            'weiban': WeibanConfigValidator(),
        },
        repr=False
    )
    
    @classmethod
    def from_yaml(cls, config_path: str = 'config/config.yaml', 
                  validate: bool = True) -> 'Config':
        """
        从 YAML 配置文件加载
        
        Args:
            config_path: 配置文件路径
            validate: 是否验证配置
            
        Returns:
            Config 实例
            
        Raises:
            ConfigError: 配置文件不存在或验证失败
        """
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(f"配置文件不存在: {config_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f) or {}
        
        # 解析数据库配置
        db_conf = raw_config.get('database', {})
        database = DatabaseConfig(
            type=db_conf.get('type', 'mysql'),
            host=db_conf.get('host', 'localhost'),
            port=db_conf.get('port', 3306),
            user=db_conf.get('user', 'root'),
            password=db_conf.get('password', ''),
            database=db_conf.get('database', 'data_sync'),
            charset=db_conf.get('charset', 'utf8mb4'),
            driver=db_conf.get('driver'),
            pool_size=db_conf.get('pool_size', 10),
        )
        
        # 解析 Redis 配置
        redis_conf = raw_config.get('redis', {})
        redis = RedisConfig(
            host=redis_conf.get('host', 'localhost'),
            port=redis_conf.get('port', 6379),
            db=redis_conf.get('db', 0),
            password=redis_conf.get('password'),
        )
        
        # 解析日志配置
        log_conf = raw_config.get('logging', {})
        logging_config = LoggingConfig(
            level=log_conf.get('level', 'INFO'),
            log_dir=log_conf.get('log_dir', 'logs'),
        )
        
        # 解析连接器配置
        # 兼容旧配置格式（wdt、weiban 等在根级别）
        connectors = raw_config.get('connectors', {})
        # 处理 wdt
        if 'wdt' in raw_config and 'wdt' not in connectors:
            connectors['wdt'] = raw_config['wdt']
            connectors['wdt']['enabled'] = True
        # 处理 weiban
        if 'weiban' in raw_config and 'weiban' not in connectors:
            connectors['weiban'] = raw_config['weiban']
            connectors['weiban']['enabled'] = True
        # 处理 wechat_store
        if 'wechat_store' in raw_config and 'wechat_store' not in connectors:
            connectors['wechat_store'] = raw_config['wechat_store']
            connectors['wechat_store']['enabled'] = True
        
        # 应用配置
        app_conf = raw_config.get('app', {})
        
        config = cls(
            app_name=app_conf.get('name', '数据同步平台'),
            env=app_conf.get('env', os.getenv('ENV', 'development')),
            debug=app_conf.get('debug', True),
            database=database,
            redis=redis,
            logging=logging_config,
            connectors=connectors,
            _raw=raw_config,
        )
        
        # 验证配置
        if validate:
            config.validate(raise_on_error=True)
        
        return config
    
    def validate(self, raise_on_error: bool = False) -> List[str]:
        """
        验证所有配置
        
        Args:
            raise_on_error: 如果有错误是否抛出异常
            
        Returns:
            错误信息列表
            
        Raises:
            ConfigError: 当 raise_on_error=True 且验证失败时
        """
        errors = []
        
        # 验证数据库配置
        db_validator = DatabaseConfigValidator()
        errors.extend(db_validator.validate(self.database.to_dict()))
        
        # 验证连接器配置
        for name, config in self.connectors.items():
            # 跳过禁用的连接器
            if not config.get('enabled', True):
                continue
            
            # 获取对应的验证器
            validator = self._connector_validators.get(name)
            if validator:
                errors.extend(validator.validate(config))
        
        if errors and raise_on_error:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ConfigError(error_msg)
        
        return errors
    
    def get_connector_config(self, connector_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定连接器的配置
        
        Args:
            connector_name: 连接器名称，如 'wdt', 'jdy'
            
        Returns:
            连接器配置字典，不存在返回 None
        """
        return self.connectors.get(connector_name)
    
    def is_connector_enabled(self, connector_name: str) -> bool:
        """检查连接器是否启用"""
        conf = self.get_connector_config(connector_name)
        if conf is None:
            return False
        return conf.get('enabled', True)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取原始配置值（支持点号路径）"""
        keys = key.split('.')
        value = self._raw
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
    
    def register_connector_validator(self, name: str, validator: ConfigValidator):
        """
        注册连接器验证器
        
        Args:
            name: 连接器名称
            validator: 验证器实例
        """
        self._connector_validators[name] = validator


# ============ 全局配置实例 ============

_config: Optional[Config] = None


def resolve_config_path(config_path: Optional[str] = None) -> str:
    """解析配置文件路径，支持 CONFIG_PATH 环境变量。"""
    if config_path:
        return config_path
    return os.getenv('CONFIG_PATH', 'config/config.yaml')


def _apply_env_overrides(config: 'Config') -> None:
    """允许 Docker / 部署环境通过环境变量覆盖部分配置。"""
    redis_host = os.getenv('REDIS_HOST')
    if redis_host:
        config.redis.host = redis_host
    redis_port = os.getenv('REDIS_PORT')
    if redis_port:
        config.redis.port = int(redis_port)
    redis_password = os.getenv('REDIS_PASSWORD')
    if redis_password is not None:
        config.redis.password = redis_password or None


def get_config(config_path: str = 'config/config.yaml', 
               reload: bool = False,
               validate: bool = True) -> Config:
    """
    获取全局配置实例
    
    Args:
        config_path: 配置文件路径
        reload: 是否强制重新加载
        validate: 是否验证配置
        
    Returns:
        Config 实例
    """
    global _config
    path = resolve_config_path(config_path if config_path != 'config/config.yaml' else None)
    if _config is None or reload:
        _config = Config.from_yaml(path, validate=validate)
        _apply_env_overrides(_config)
    return _config


def validate_config(config_path: str = 'config/config.yaml') -> List[str]:
    """
    独立验证配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        错误信息列表，空列表表示验证通过
    """
    try:
        path = resolve_config_path(config_path if config_path != 'config/config.yaml' else None)
        config = Config.from_yaml(path, validate=False)
        _apply_env_overrides(config)
        return config.validate()
    except Exception as e:
        return [str(e)]
