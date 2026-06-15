# -*- coding: utf-8 -*-
"""
系统配置管理 - Pydantic V2 Settings
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """系统配置"""

    # TDengine 配置
    tdengine_host: str = "tdengine"
    tdengine_port: int = 6030
    tdengine_rest_port: int = 6041
    tdengine_user: str = "root"
    tdengine_password: str = "taosdata"
    tdengine_database: str = "quant_db"

    # pytdx 配置
    pytdx_hosts: str = "60.12.136.250,218.75.126.9,115.238.56.198,60.191.117.167,180.153.18.170,115.238.90.165"
    pytdx_port: int = 7709

    # QMT 配置
    qmt_path: str = "/data/qmt"
    qmt_host: str = "127.0.0.1"
    qmt_port: int = 18080

    # modtdx 配置
    modtdx_enabled: bool = False

    # 采集配置
    collect_interval: int = 5
    max_retry: int = 3
    batch_size: int = 1000
    cache_size: int = 10000
    collect_timeout: int = 30

    # JWT 认证
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Redis 配置
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0

    # PostgreSQL 配置
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "quant_user"
    postgres_password: str = "quant_pass"
    postgres_db: str = "quant_db"

    # RabbitMQ 配置
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "quant_user"
    rabbitmq_pass: str = "quant_pass"
    rabbitmq_vhost: str = "/"

    # API 配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    cors_origins: str = "*"

    # 日志配置
    log_level: str = "INFO"
    log_dir: str = "/app/logs"

    # 数据类型配置
    data_types: str = "stock,futures,index,sector"
    kline_intervals: str = "1min,5min,15min,30min,60min,1day,1week,1month"

    # 时区
    tz: str = "Asia/Shanghai"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def pytdx_host_list(self) -> List[str]:
        return [h.strip() for h in self.pytdx_hosts.split(",") if h.strip()]

    @property
    def data_type_list(self) -> List[str]:
        return [t.strip() for t in self.data_types.split(",") if t.strip()]

    @property
    def kline_interval_list(self) -> List[str]:
        return [k.strip() for k in self.kline_intervals.split(",") if k.strip()]

    @property
    def cors_origin_list(self) -> List[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取配置实例"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# 导出默认配置实例
settings = get_settings()
