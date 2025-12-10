"""
SQLAlchemy models for quota and rate limiting storage

Uses the same database as aipartnerupflow (DuckDB/PostgreSQL).
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

# Use the same Base as aipartnerupflow
from aipartnerupflow.core.storage.sqlalchemy.models import Base


class QuotaCounter(Base):
    """
    Daily quota counter for users
    
    Stores daily task tree counts and LLM-consuming task tree counts.
    """
    __tablename__ = "demo_quota_counters"
    
    # Composite primary key: user_id + date + counter_type
    user_id = Column(String(255), primary_key=True, nullable=False, index=True)
    date = Column(String(10), primary_key=True, nullable=False)  # ISO date format: YYYY-MM-DD
    counter_type = Column(String(50), primary_key=True, nullable=False)  # 'total' or 'llm'
    
    count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_quota_user_date', 'user_id', 'date'),
    )


class ConcurrencyCounter(Base):
    """
    Concurrency counter for task trees
    
    Tracks currently running task trees (system-wide and per-user).
    """
    __tablename__ = "demo_concurrency_counters"
    
    # Composite primary key: scope + identifier
    scope = Column(String(50), primary_key=True, nullable=False)  # 'system' or 'user'
    identifier = Column(String(255), primary_key=True, nullable=False)  # 'global' or user_id
    
    count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_concurrency_scope', 'scope', 'identifier'),
    )


class TaskTreeTracking(Base):
    """
    Task tree tracking for quota management
    
    Tracks active task trees to manage concurrency and quota.
    """
    __tablename__ = "demo_task_tree_tracking"
    
    task_tree_id = Column(String(255), primary_key=True, nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    is_llm_consuming = Column(String(10), nullable=False, default='false')  # 'true' or 'false' (stored as string for compatibility)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index('idx_task_tree_user', 'user_id'),
        Index('idx_task_tree_active', 'user_id', 'completed_at'),
    )


class UsageStats(Base):
    """
    Usage statistics tracking
    
    Tracks daily usage statistics for tasks and demo mode.
    """
    __tablename__ = "demo_usage_stats"
    
    # Composite primary key: date + stat_type + identifier
    date = Column(String(10), primary_key=True, nullable=False)  # ISO date format: YYYY-MM-DD
    stat_type = Column(String(50), primary_key=True, nullable=False)  # 'total', 'demo', 'user'
    identifier = Column(String(255), primary_key=True, nullable=False)  # 'global' or user_id
    
    count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_usage_date_type', 'date', 'stat_type'),
        Index('idx_usage_user', 'stat_type', 'identifier'),
    )

