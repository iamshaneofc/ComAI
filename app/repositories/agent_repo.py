"""
Agent Repository — DB access for per-store channel agents.

No fallback or business rules; see AgentService.
"""
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.repositories.base import BaseRepository


class AgentRepository(BaseRepository[Agent]):
    """Agent-specific data access."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Agent, db=db)

    async def get_by_type(self, store_id: UUID, agent_type: str) -> Agent | None:
        """Active agent for store + channel type, most recently updated wins."""
        result = await self.db.execute(
            select(Agent)
            .where(
                Agent.store_id == store_id,
                Agent.type == agent_type,
                Agent.is_active.is_(True),
            )
            .order_by(Agent.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_agents(self, store_id: UUID) -> list[Agent]:
        """All active agents for a tenant, ordered by type then name."""
        result = await self.db.execute(
            select(Agent)
            .where(Agent.store_id == store_id, Agent.is_active.is_(True))
            .order_by(Agent.type, Agent.name)
        )
        return list(result.scalars().all())

    async def get_by_id_for_store(self, store_id: UUID, agent_id: UUID) -> Agent | None:
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id, Agent.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def list_for_store(self, store_id: UUID, *, active_only: bool = False) -> list[Agent]:
        stmt = select(Agent).where(Agent.store_id == store_id)
        if active_only:
            stmt = stmt.where(Agent.is_active.is_(True))
        stmt = stmt.order_by(Agent.type, Agent.name, Agent.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def deactivate_others_same_type(
        self,
        store_id: UUID,
        agent_type: str,
        keep_agent_id: UUID,
    ) -> None:
        """Ensure a single active agent per (store, type): deactivate all other active rows."""
        await self.db.execute(
            update(Agent)
            .where(
                Agent.store_id == store_id,
                Agent.type == agent_type,
                Agent.id != keep_agent_id,
                Agent.is_active.is_(True),
            )
            .values(is_active=False)
        )
        await self.db.flush()
