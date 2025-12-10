"""
Repository for quota and rate limiting data

Uses SQLAlchemy to store quota data in the same database as aipartnerupflow.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import and_, func as sql_func
from sqlalchemy.orm import Session

from aipartnerupflow_demo.storage.models import (
    QuotaCounter,
    ConcurrencyCounter,
    TaskTreeTracking,
    UsageStats,
)


class QuotaRepository:
    """Repository for quota and rate limiting data"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_quota_count(
        self,
        user_id: str,
        date: str,
        counter_type: str = "total"
    ) -> int:
        """
        Get quota count for user on a specific date
        
        Args:
            user_id: User ID
            date: Date in ISO format (YYYY-MM-DD)
            counter_type: 'total' or 'llm'
            
        Returns:
            Count (0 if not found)
        """
        counter = self.session.query(QuotaCounter).filter(
            and_(
                QuotaCounter.user_id == user_id,
                QuotaCounter.date == date,
                QuotaCounter.counter_type == counter_type,
            )
        ).first()
        
        return counter.count if counter else 0
    
    def increment_quota_count(
        self,
        user_id: str,
        date: str,
        counter_type: str = "total",
        amount: int = 1
    ) -> int:
        """
        Increment quota count for user on a specific date
        
        Args:
            user_id: User ID
            date: Date in ISO format (YYYY-MM-DD)
            counter_type: 'total' or 'llm'
            amount: Amount to increment (default: 1)
            
        Returns:
            New count after increment
        """
        counter = self.session.query(QuotaCounter).filter(
            and_(
                QuotaCounter.user_id == user_id,
                QuotaCounter.date == date,
                QuotaCounter.counter_type == counter_type,
            )
        ).first()
        
        if counter:
            counter.count += amount
            counter.updated_at = datetime.now(timezone.utc)
        else:
            counter = QuotaCounter(
                user_id=user_id,
                date=date,
                counter_type=counter_type,
                count=amount,
            )
            self.session.add(counter)
        
        self.session.commit()
        return counter.count
    
    def get_concurrency_count(
        self,
        scope: str,
        identifier: str
    ) -> int:
        """
        Get concurrency count
        
        Args:
            scope: 'system' or 'user'
            identifier: 'global' for system, user_id for user
            
        Returns:
            Count (0 if not found)
        """
        counter = self.session.query(ConcurrencyCounter).filter(
            and_(
                ConcurrencyCounter.scope == scope,
                ConcurrencyCounter.identifier == identifier,
            )
        ).first()
        
        return counter.count if counter else 0
    
    def increment_concurrency(
        self,
        scope: str,
        identifier: str,
        amount: int = 1
    ) -> int:
        """
        Increment concurrency count
        
        Args:
            scope: 'system' or 'user'
            identifier: 'global' for system, user_id for user
            amount: Amount to increment (default: 1)
            
        Returns:
            New count after increment
        """
        counter = self.session.query(ConcurrencyCounter).filter(
            and_(
                ConcurrencyCounter.scope == scope,
                ConcurrencyCounter.identifier == identifier,
            )
        ).first()
        
        if counter:
            counter.count += amount
            counter.updated_at = datetime.now(timezone.utc)
        else:
            counter = ConcurrencyCounter(
                scope=scope,
                identifier=identifier,
                count=amount,
            )
            self.session.add(counter)
        
        self.session.commit()
        return counter.count
    
    def decrement_concurrency(
        self,
        scope: str,
        identifier: str,
        amount: int = 1
    ) -> int:
        """
        Decrement concurrency count
        
        Args:
            scope: 'system' or 'user'
            identifier: 'global' for system, user_id for user
            amount: Amount to decrement (default: 1)
            
        Returns:
            New count after decrement (minimum 0)
        """
        counter = self.session.query(ConcurrencyCounter).filter(
            and_(
                ConcurrencyCounter.scope == scope,
                ConcurrencyCounter.identifier == identifier,
            )
        ).first()
        
        if counter:
            counter.count = max(0, counter.count - amount)
            counter.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            return counter.count
        
        return 0
    
    def start_task_tree(
        self,
        task_tree_id: str,
        user_id: str,
        is_llm_consuming: bool
    ) -> None:
        """
        Start tracking a task tree
        
        Args:
            task_tree_id: Task tree ID
            user_id: User ID
            is_llm_consuming: Whether task tree is LLM-consuming
        """
        tracking = TaskTreeTracking(
            task_tree_id=task_tree_id,
            user_id=user_id,
            is_llm_consuming='true' if is_llm_consuming else 'false',
        )
        self.session.add(tracking)
        self.session.commit()
    
    def complete_task_tree(
        self,
        task_tree_id: str
    ) -> Optional[TaskTreeTracking]:
        """
        Mark task tree as completed
        
        Args:
            task_tree_id: Task tree ID
            
        Returns:
            TaskTreeTracking object if found, None otherwise
        """
        tracking = self.session.query(TaskTreeTracking).filter(
            TaskTreeTracking.task_tree_id == task_tree_id
        ).first()
        
        if tracking:
            tracking.completed_at = datetime.now(timezone.utc)
            self.session.commit()
        
        return tracking
    
    def get_active_task_tree(
        self,
        task_tree_id: str
    ) -> Optional[TaskTreeTracking]:
        """
        Get active task tree tracking
        
        Args:
            task_tree_id: Task tree ID
            
        Returns:
            TaskTreeTracking object if found and active, None otherwise
        """
        return self.session.query(TaskTreeTracking).filter(
            and_(
                TaskTreeTracking.task_tree_id == task_tree_id,
                TaskTreeTracking.completed_at.is_(None),
            )
        ).first()
    
    def get_user_active_task_trees(
        self,
        user_id: str
    ) -> list[TaskTreeTracking]:
        """
        Get all active task trees for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of active TaskTreeTracking objects
        """
        return self.session.query(TaskTreeTracking).filter(
            and_(
                TaskTreeTracking.user_id == user_id,
                TaskTreeTracking.completed_at.is_(None),
            )
        ).all()
    
    def increment_usage_stat(
        self,
        date: str,
        stat_type: str,
        identifier: str,
        amount: int = 1
    ) -> int:
        """
        Increment usage statistic
        
        Args:
            date: Date in ISO format (YYYY-MM-DD)
            stat_type: 'total', 'demo', or 'user'
            identifier: 'global' for total/demo, user_id for user
            amount: Amount to increment (default: 1)
            
        Returns:
            New count after increment
        """
        stat = self.session.query(UsageStats).filter(
            and_(
                UsageStats.date == date,
                UsageStats.stat_type == stat_type,
                UsageStats.identifier == identifier,
            )
        ).first()
        
        if stat:
            stat.count += amount
            stat.updated_at = datetime.now(timezone.utc)
        else:
            stat = UsageStats(
                date=date,
                stat_type=stat_type,
                identifier=identifier,
                count=amount,
            )
            self.session.add(stat)
        
        self.session.commit()
        return stat.count
    
    def get_usage_stat(
        self,
        date: str,
        stat_type: str,
        identifier: str
    ) -> int:
        """
        Get usage statistic
        
        Args:
            date: Date in ISO format (YYYY-MM-DD)
            stat_type: 'total', 'demo', or 'user'
            identifier: 'global' for total/demo, user_id for user
            
        Returns:
            Count (0 if not found)
        """
        stat = self.session.query(UsageStats).filter(
            and_(
                UsageStats.date == date,
                UsageStats.stat_type == stat_type,
                UsageStats.identifier == identifier,
            )
        ).first()
        
        return stat.count if stat else 0
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """
        Clean up old quota and usage data
        
        Args:
            days_to_keep: Number of days to keep (default: 30)
            
        Returns:
            Number of records deleted
        """
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_to_keep)).date().isoformat()
        
        # Delete old quota counters
        quota_deleted = self.session.query(QuotaCounter).filter(
            QuotaCounter.date < cutoff_date
        ).delete()
        
        # Delete old usage stats
        usage_deleted = self.session.query(UsageStats).filter(
            UsageStats.date < cutoff_date
        ).delete()
        
        # Delete completed task tree tracking older than cutoff
        tracking_deleted = self.session.query(TaskTreeTracking).filter(
            and_(
                TaskTreeTracking.completed_at.isnot(None),
                sql_func.date(TaskTreeTracking.completed_at) < cutoff_date,
            )
        ).delete()
        
        self.session.commit()
        return quota_deleted + usage_deleted + tracking_deleted

