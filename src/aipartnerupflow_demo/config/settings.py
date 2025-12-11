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
    
    # aipartnerupflow configuration (passed through)
    aipartnerupflow_api_protocol: str = os.getenv("AIPARTNERUPFLOW_API_PROTOCOL", "a2a")
    aipartnerupflow_api_host: str = os.getenv("AIPARTNERUPFLOW_API_HOST", os.getenv("API_HOST", "0.0.0.0"))
    aipartnerupflow_api_port: int = int(os.getenv("AIPARTNERUPFLOW_API_PORT", os.getenv("PORT", "8000")))
    aipartnerupflow_base_url: Optional[str] = os.getenv("AIPARTNERUPFLOW_BASE_URL")
    
    # JWT (optional, defaults to demo secret key if not provided)
    aipartnerupflow_jwt_secret_key: Optional[str] = os.getenv(
        "AIPARTNERUPFLOW_JWT_SECRET_KEY",
        os.getenv("JWT_SECRET_KEY", "demo-secret-key-change-in-production")
    )
    aipartnerupflow_jwt_algorithm: str = os.getenv("AIPARTNERUPFLOW_JWT_ALGORITHM", "HS256")
    
    # System routes and docs
    aipartnerupflow_enable_system_routes: bool = os.getenv("AIPARTNERUPFLOW_ENABLE_SYSTEM_ROUTES", "true").lower() in ("true", "1", "yes")
    aipartnerupflow_enable_docs: bool = os.getenv("AIPARTNERUPFLOW_ENABLE_DOCS", "true").lower() in ("true", "1", "yes")
    
    def get_aipartnerupflow_env(self) -> dict[str, str]:
        """Get environment variables for aipartnerupflow"""
        env = {}
        if self.aipartnerupflow_api_protocol:
            env["AIPARTNERUPFLOW_API_PROTOCOL"] = self.aipartnerupflow_api_protocol
        if self.aipartnerupflow_api_host:
            env["AIPARTNERUPFLOW_API_HOST"] = self.aipartnerupflow_api_host
        if self.aipartnerupflow_api_port:
            env["AIPARTNERUPFLOW_API_PORT"] = str(self.aipartnerupflow_api_port)
        if self.aipartnerupflow_base_url:
            env["AIPARTNERUPFLOW_BASE_URL"] = self.aipartnerupflow_base_url
        if self.aipartnerupflow_jwt_secret_key:
            env["AIPARTNERUPFLOW_JWT_SECRET_KEY"] = self.aipartnerupflow_jwt_secret_key
        if self.aipartnerupflow_jwt_algorithm:
            env["AIPARTNERUPFLOW_JWT_ALGORITHM"] = self.aipartnerupflow_jwt_algorithm
        if self.aipartnerupflow_enable_system_routes:
            env["AIPARTNERUPFLOW_ENABLE_SYSTEM_ROUTES"] = str(self.aipartnerupflow_enable_system_routes).lower()
        if self.aipartnerupflow_enable_docs:
            env["AIPARTNERUPFLOW_ENABLE_DOCS"] = str(self.aipartnerupflow_enable_docs).lower()
        return env


# Global settings instance
settings = DemoSettings()

