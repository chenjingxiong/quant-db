# -*- coding: utf-8 -*-
"""
系统配置管理
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """系统配置"""

    # TDengine 配置
    tdengine_host: str = Field(default="tdengine", env="TDENGINE_HOST")
    tdengine_port: int = Field(default=6030, env="TDENGINE_PORT")
    tdengine_user: str = Field(default="root", env="TDENGINE_USER")
    tdengine_password: str = Field(default="taosdata", env="TDENGINE_PASSWORD")
    tdengine_database: str = Field(default="quant_db", env="TDENGINE_DATABASE")

    # pytdx 配置
    pytdx_hosts: str = Field(
        default="119.147.212.81,60.12.136.250",
        env="PYTDX_HOSTS"
    )
    pytdx_port: int = Field(default=7709, env="PYTDX_PORT")

    # QMT 配置
    qmt_path: str = Field(default="/data/qmt", env="QMT_PATH")
    qmt_host: str = Field(default="127.0.0.1", env="QMT_HOST")
    qmt_port: int = Field(default=18080, env="QMT_PORT")

    # modtdx 配置
    modtdx_enabled: bool = Field(default=False, env="MODTDX_ENABLED")

    # 采集配置
    collect_interval: int = Field(default=5, env="COLLECT_INTERVAL")
    max_retry: int = Field(default=3, env="MAX_RETRY")
    batch_size: int = Field(default=1000, env="BATCH_SIZE")
    cache_size: int = Field(default=10000, env="CACHE_SIZE")
    collect_timeout: int = Field(default=30, env="COLLECT_TIMEOUT")

    # JWT 认证
    jwt_secret_key: str = Field(default="your-secret-key-change-in-production", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # Redis 配置
    redis_host: str = Field(default="redis", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")

    # PostgreSQL 配置
    postgres_host: str = Field(default="postgres", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_user: str = Field(default="quant_user", env="POSTGRES_USER")
    postgres_password: str = Field(default="quant_pass", env="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="quant_db", env="POSTGRES_DB")

    # RabbitMQ 配置
    rabbitmq_host: str = Field(default="rabbitmq", env="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, env="RABBITMQ_PORT")
    rabbitmq_user: str = Field(default="quant_user", env="RABBITMQ_USER")
    rabbitmq_pass: str = Field(default="quant_pass", env="RABBITMQ_PASS")
    rabbitmq_vhost: str = Field(default="/", env="RABBITMQ_VHOST")

    # API 配置
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")

    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_dir: str = Field(default="/app/logs", env="LOG_DIR")

    # 数据类型配置
    data_types: str = Field(default="stock,futures,index,sector", env="DATA_TYPES")
    kline_intervals: str = Field(
        default="1min,5min,15min,30min,60min,1day,1week,1month",
        env="KL_INTERVALS"
    )

    # 时区
    tz: str = Field(default="Asia/Shanghai", env="TZ")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def pytdx_host_list(self) -> List[str]:
        """获取pytdx服务器列表"""
        return [h.strip() for h in self.pytdx_hosts.split(",") if h.strip()]

    @property
    def data_type_list(self) -> List[str]:
        """获取数据类型列表"""
        return [t.strip() for t in self.data_types.split(",") if t.strip()]

    @property
    def kline_interval_list(self) -> List[str]:
        """获取K线周期列表"""
        return [k.strip() for k in self.kline_intervals.split(",") if k.strip()]

    @property
    def cors_origin_list(self) -> List[str]:
        """获取CORS允许源列表"""
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
