"""
Repository for quota and rate limiting data

Uses SQLAlchemy to store quota data in the same database as apflow.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Union, List
from sqlalchemy import and_, func as sql_func, select, delete
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_session_proxy import SqlalchemySessionProxy

from apflow_demo.storage.models import (
    QuotaCounter,
    ConcurrencyCounter,
    TaskTreeTracking,
    UsageStats,
)


class QuotaRepository:
    """Repository for quota and rate limiting data"""
    
    def __init__(self, session: Union[Session, AsyncSession]):
        self.session = SqlalchemySessionProxy(session)
    
    async def get_quota_count(
        self,
        user_id: str,
        date: str,
        counter_type: str = "total"
    ) -> int:
        """
        Get quota count for user on a specific date
        """
        stmt = select(QuotaCounter).filter(
            and_(
                QuotaCounter.user_id == user_id,
                QuotaCounter.date == date,
                QuotaCounter.counter_type == counter_type,
            )
        )
        
        result = await self.session.execute(stmt)
        
        counter = result.scalar_one_or_none()
        return counter.count if counter else 0
    
    async def increment_quota_count(
        self,
        user_id: str,
        date: str,
        counter_type: str = "total",
        amount: int = 1
    ) -> int:
        """
        Increment quota count for user on a specific date
        """
        stmt = select(QuotaCounter).filter(
            and_(
                QuotaCounter.user_id == user_id,
                QuotaCounter.date == date,
                QuotaCounter.counter_type == counter_type,
            )
        )
        
        result = await self.session.execute(stmt)
            
        counter = result.scalar_one_or_none()
        
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
        
        await self.session.commit()
            
        return counter.count
    
    async def get_concurrency_count(
        self,
        scope: str,
        identifier: str
    ) -> int:
        """
        Get concurrency count
        """
        stmt = select(ConcurrencyCounter).filter(
            and_(
                ConcurrencyCounter.scope == scope,
                ConcurrencyCounter.identifier == identifier,
            )
        )
        
        result = await self.session.execute(stmt)
            
        counter = result.scalar_one_or_none()
        return counter.count if counter else 0
    
    async def increment_concurrency(
        self,
        scope: str,
        identifier: str,
        amount: int = 1
    ) -> int:
        """
        Increment concurrency count
        """
        stmt = select(ConcurrencyCounter).filter(
            and_(
                ConcurrencyCounter.scope == scope,
                ConcurrencyCounter.identifier == identifier,
            )
        )
        
        result = await self.session.execute(stmt)
            
        counter = result.scalar_one_or_none()
        
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
        
        await self.session.commit()
            
        return counter.count
    
    async def decrement_concurrency(
        self,
        scope: str,
        identifier: str,
        amount: int = 1
    ) -> int:
        """
        Decrement concurrency count
        """
        stmt = select(ConcurrencyCounter).filter(
            and_(
                ConcurrencyCounter.scope == scope,
                ConcurrencyCounter.identifier == identifier,
            )
        )
        
        result = await self.session.execute(stmt)
            
        counter = result.scalar_one_or_none()
        
        if counter:
            counter.count = max(0, counter.count - amount)
            counter.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return counter.count
        
        return 0
    
    async def start_task_tree(
        self,
        task_tree_id: str,
        user_id: str,
        is_llm_consuming: bool
    ) -> None:
        """
        Start tracking a task tree
        """
        tracking = TaskTreeTracking(
            task_tree_id=task_tree_id,
            user_id=user_id,
            is_llm_consuming='true' if is_llm_consuming else 'false',
        )
        self.session.add(tracking)
        await self.session.commit()
    
    async def complete_task_tree(
        self,
        task_tree_id: str
    ) -> Optional[TaskTreeTracking]:
        """
        Mark task tree as completed
        """
        stmt = select(TaskTreeTracking).filter(
            TaskTreeTracking.task_tree_id == task_tree_id
        )
        
        result = await self.session.execute(stmt)
            
        tracking = result.scalar_one_or_none()
        
        if tracking:
            tracking.completed_at = datetime.now(timezone.utc)
            await self.session.commit()
        
        return tracking
    
    async def get_active_task_tree(
        self,
        task_tree_id: str
    ) -> Optional[TaskTreeTracking]:
        """
        Get active task tree tracking
        """
        stmt = select(TaskTreeTracking).filter(
            and_(
                TaskTreeTracking.task_tree_id == task_tree_id,
                TaskTreeTracking.completed_at.is_(None),
            )
        )
        
        result = await self.session.execute(stmt)
            
        return result.scalar_one_or_none()
    
    async def get_user_active_task_trees(
        self,
        user_id: str
    ) -> List[TaskTreeTracking]:
        """
        Get all active task trees for a user
        """
        stmt = select(TaskTreeTracking).filter(
            and_(
                TaskTreeTracking.user_id == user_id,
                TaskTreeTracking.completed_at.is_(None),
            )
        )
        
        result = await self.session.execute(stmt)
            
        return result.scalars().all()
    
    async def increment_usage_stat(
        self,
        date: str,
        stat_type: str,
        identifier: str,
        amount: int = 1
    ) -> int:
        """
        Increment usage statistic
        """
        stmt = select(UsageStats).filter(
            and_(
                UsageStats.date == date,
                UsageStats.stat_type == stat_type,
                UsageStats.identifier == identifier,
            )
        )
        
        result = await self.session.execute(stmt)
            
        stat = result.scalar_one_or_none()
        
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
        
        await self.session.commit()
            
        return stat.count
    
    async def get_usage_stat(
        self,
        date: str,
        stat_type: str,
        identifier: str
    ) -> int:
        """
        Get usage statistic
        """
        stmt = select(UsageStats).filter(
            and_(
                UsageStats.date == date,
                UsageStats.stat_type == stat_type,
                UsageStats.identifier == identifier,
            )
        )
        
        result = await self.session.execute(stmt)
            
        stat = result.scalar_one_or_none()
        return stat.count if stat else 0
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """
        Clean up old quota and usage data
        """
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_to_keep)).date().isoformat()
        
        # Delete old quota counters
        quota_stmt = delete(QuotaCounter).where(QuotaCounter.date < cutoff_date)
        
        # Delete old usage stats
        usage_stmt = delete(UsageStats).where(UsageStats.date < cutoff_date)
        
        # Delete completed task tree tracking older than cutoff
        tracking_stmt = delete(TaskTreeTracking).where(
            and_(
                TaskTreeTracking.completed_at.isnot(None),
                sql_func.date(TaskTreeTracking.completed_at) < cutoff_date,
            )
        )
        
        r1 = await self.session.execute(quota_stmt)
        r2 = await self.session.execute(usage_stmt)
        r3 = await self.session.execute(tracking_stmt)
        await self.session.commit()
            
        return r1.rowcount + r2.rowcount + r3.rowcount

