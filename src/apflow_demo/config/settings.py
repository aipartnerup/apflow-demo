"""
Demo settings configuration
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class DemoSettings(BaseSettings):
    """Demo application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Demo mode
    demo_mode: bool = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "false").lower() in ("true", "1", "yes")
    
    # Rate limiting
    rate_limit_daily_per_user: int = int(os.getenv("RATE_LIMIT_DAILY_PER_USER", "10"))
    rate_limit_daily_per_ip: int = int(os.getenv("RATE_LIMIT_DAILY_PER_IP", "50"))
    
    # LLM-consuming task tree limits
    rate_limit_daily_llm_per_user: int = int(os.getenv("RATE_LIMIT_DAILY_LLM_PER_USER", "1"))  # Free users: only 1 LLM-consuming task tree
    rate_limit_daily_per_user_premium: int = int(os.getenv("RATE_LIMIT_DAILY_PER_USER_PREMIUM", "10"))  # Premium users: 10 total (no separate LLM limit)
    
    # Concurrency limits
    max_concurrent_task_trees: int = int(os.getenv("MAX_CONCURRENT_TASK_TREES", "10"))  # System-wide
    max_concurrent_task_trees_per_user: int = int(os.getenv("MAX_CONCURRENT_TASK_TREES_PER_USER", "1"))  # Per-user
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    
    # apflow configuration (passed through)
    apflow_api_protocol: str = os.getenv("APFLOW_API_PROTOCOL", "a2a")
    apflow_api_host: str = os.getenv("APFLOW_API_HOST", os.getenv("API_HOST", "0.0.0.0"))
    apflow_api_port: int = int(os.getenv("APFLOW_API_PORT", os.getenv("PORT", "8000")))
    apflow_base_url: Optional[str] = os.getenv("APFLOW_BASE_URL")
    
    # JWT (optional, defaults to demo secret key if not provided)
    apflow_jwt_secret_key: Optional[str] = os.getenv(
        "APFLOW_JWT_SECRET_KEY",
        os.getenv("JWT_SECRET_KEY", "demo-secret-key-change-in-production")
    )
    apflow_jwt_algorithm: str = os.getenv("APFLOW_JWT_ALGORITHM", "HS256")
    
    # System routes and docs
    apflow_enable_system_routes: bool = os.getenv("APFLOW_ENABLE_SYSTEM_ROUTES", "true").lower() in ("true", "1", "yes")
    apflow_enable_docs: bool = os.getenv("APFLOW_ENABLE_DOCS", "true").lower() in ("true", "1", "yes")
    
    # CORS origins
    apflow_cors_origins: Optional[str] = os.getenv("APFLOW_CORS_ORIGINS")
    
    # Database URL
    database_url: Optional[str] = os.getenv("DATABASE_URL")
    
    def get_apflow_env(self) -> dict[str, str]:
        """Get environment variables for apflow"""
        env = {}
        if self.apflow_api_protocol:
            env["APFLOW_API_PROTOCOL"] = self.apflow_api_protocol
        if self.apflow_api_host:
            env["APFLOW_API_HOST"] = self.apflow_api_host
        if self.apflow_api_port:
            env["APFLOW_API_PORT"] = str(self.apflow_api_port)
        if self.apflow_base_url:
            env["APFLOW_BASE_URL"] = self.apflow_base_url
        if self.apflow_jwt_secret_key:
            env["APFLOW_JWT_SECRET_KEY"] = self.apflow_jwt_secret_key
        if self.apflow_jwt_algorithm:
            env["APFLOW_JWT_ALGORITHM"] = self.apflow_jwt_algorithm
        if self.apflow_enable_system_routes:
            env["APFLOW_ENABLE_SYSTEM_ROUTES"] = str(self.apflow_enable_system_routes).lower()
        if self.apflow_enable_docs:
            env["APFLOW_ENABLE_DOCS"] = str(self.apflow_enable_docs).lower()
        # Add CORS origins
        if self.apflow_cors_origins:
            env["APFLOW_CORS_ORIGINS"] = self.apflow_cors_origins
        # Add DATABASE_URL
        if self.database_url:
            env["DATABASE_URL"] = self.database_url
        return env


# Global settings instance
settings = DemoSettings()

