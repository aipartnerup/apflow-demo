"""
CLI extension for user management and statistics
"""

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.ext.asyncio import AsyncSession
from apflow.cli import CLIExtension
from apflow_demo.services.user_service import user_tracking_service

# Initialize UI
console = Console()

# Create and register the command group using decorator
# This automatically registers with apflow CLI without entry points



@cli_register(name="users", help="Manage and analyze users")
class UsersApp(CLIExtension):
    """CLI extension for user management."""

    def __init__(self):
        super().__init__(help="Manage and analyze users")

        # Register commands as instance methods
        self.command()(self.stat)
        self.command()(self.list)

    def stat(
        self,
        period: str = typer.Argument(
            "all", help="Statistics period: all, day, week, month, year"
        ),
        output_format: str = typer.Option(
            "table", "--format", "-f", help="Output format: table, json"
        ),
    ):
        """
        Display user statistics for a given period
        
        Example: apflow users stat day
        """
        valid_periods = ["all", "day", "week", "month", "year"]
        if period not in valid_periods:
            console.print(f"[red]Error:[/red] Invalid period '{period}'. Valid options: {', '.join(valid_periods)}")
            raise typer.Exit(code=1)

        async def _get_stats():
            return await user_tracking_service.get_user_stats(period)

<<<<<<< HEAD:src/apflow_demo/cli/users.py

@users_app.command()
def list(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of users to display"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    output_format: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json"
    ),
    show_ua: bool = typer.Option(False, "--show-ua", help="Show User-Agent in table output")
):
    """
    List demo users (latest active first)
    """
    from sqlalchemy import select
    from sqlalchemy.sql import desc
    from apflow.core.storage import create_pooled_session
    from apflow_demo.storage.models import DemoUser

    async def _list_users():
        async with create_pooled_session() as session:
            stmt = select(DemoUser).order_by(desc(DemoUser.last_active_at)).limit(limit)
            if status:
                stmt = stmt.where(DemoUser.status == status)
=======
        try:
            stats = asyncio.run(_get_stats())
>>>>>>> f3c6c122c8f55bb48c02e0390200254dfc406664:src/apflow_demo/cli/users.py
            
            if output_format == "json":
                console.print(json.dumps(stats, indent=2))
                return

            table = Table(title=f"User Statistics ({period})")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Users", str(stats["total_users"]))
            table.add_row(f"Active Users ({period})", str(stats["active_users"]))
            table.add_row(f"New Users ({period})", str(stats["new_users"]))
            
            console.print(table)
            console.print(f"[dim]Generated at: {stats['timestamp']}[/dim]")
            
        except Exception as e:
            console.print(f"[red]Error fetching statistics:[/red] {str(e)}")
            raise typer.Exit(code=1)

    def list(
        self,
        limit: int = typer.Option(20, "--limit", "-l", help="Number of users to display"),
        status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
        output_format: str = typer.Option(
            "table", "--format", "-f", help="Output format: table, json"
        ),
        show_ua: bool = typer.Option(False, "--show-ua", help="Show User-Agent in table output")
    ):
        """
        List demo users (latest active first)
        """
        from sqlalchemy import select
        from sqlalchemy.sql import desc
        from apflow.core.storage import create_pooled_session
        from apflow_demo.storage.models import DemoUser

        async def _list_users():
            async with create_pooled_session() as session:
                stmt = select(DemoUser).order_by(desc(DemoUser.last_active_at)).limit(limit)
                if status:
                    stmt = stmt.where(DemoUser.status == status)
                
                if isinstance(session, AsyncSession):
                    result = await session.execute(stmt)
                    return result.scalars().all()
                else:
                    result = session.execute(stmt)
                    return result.scalars().all()

        try:
            users = asyncio.run(_list_users())
            
            if not users:
                if output_format == "json":
                    console.print("[]")
                else:
                    console.print("No users found.")
                return

            if output_format == "json":
                users_data = []
                for user in users:
                    users_data.append({
                        "user_id": user.user_id,
                        "username": user.username,
                        "status": user.status,
                        "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
                        "source": user.source,
                        "user_agent": user.user_agent,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                    })
                console.print(json.dumps(users_data, indent=2))
                return

            table = Table(title=f"Latest Users (Top {limit})")
            table.add_column("User ID", style="dim")
            table.add_column("Username", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Last Active", style="magenta")
            table.add_column("Source", style="yellow")
            if show_ua:
                table.add_column("User-Agent", style="dim")
            
            for user in users:
                table.add_row(
                    user.user_id[:20] + "..." if len(user.user_id) > 20 else user.user_id,
                    user.username,
                    user.status,
                    user.last_active_at.strftime("%Y-%m-%d %H:%M:%S") if user.last_active_at else "N/A",
                    user.source or "unknown"
                )
                if show_ua:
                    ua = user.user_agent or "N/A"
                    table.add_row("", "", "", "", "", ua)
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Error listing users:[/red] {str(e)}")
            raise typer.Exit(code=1)
