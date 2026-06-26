from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.database import get_session
from app.infrastructure.persistence.models import Strategy
from app.domain.strategy.engine import STRATEGY_TEMPLATES

router = APIRouter(tags=["strategy"])


class StrategyCreate(BaseModel):
    name: str
    description: str = ""
    code: str
    params: dict = {}


class StrategyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    code: str | None = None
    params: dict | None = None


@router.get("/templates")
async def list_templates():
    """Return built-in strategy templates."""
    return STRATEGY_TEMPLATES


@router.get("/")
async def list_strategies(session: AsyncSession = Depends(get_session)):
    stmt = select(Strategy).order_by(Strategy.updated_at.desc()).limit(50)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [{
        "id": str(r.id), "name": r.name, "description": r.description,
        "params": r.params, "created_at": str(r.created_at),
        "updated_at": str(r.updated_at),
    } for r in rows]


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str,
                       session: AsyncSession = Depends(get_session)):
    stmt = select(Strategy).where(Strategy.id == strategy_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Strategy not found")
    return {
        "id": str(row.id), "name": row.name, "description": row.description,
        "code": row.code, "params": row.params,
        "created_at": str(row.created_at), "updated_at": str(row.updated_at),
    }


@router.post("/")
async def create_strategy(data: StrategyCreate,
                          session: AsyncSession = Depends(get_session)):
    strategy = Strategy(**data.model_dump())
    session.add(strategy)
    await session.commit()
    await session.refresh(strategy)
    return {"id": str(strategy.id), "name": strategy.name}


@router.put("/{strategy_id}")
async def update_strategy(strategy_id: str, data: StrategyUpdate,
                          session: AsyncSession = Depends(get_session)):
    stmt = select(Strategy).where(Strategy.id == strategy_id)
    result = await session.execute(stmt)
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(404, "Strategy not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(strategy, key, value)
    await session.commit()
    return {"id": str(strategy.id), "updated": True}


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: str,
                          session: AsyncSession = Depends(get_session)):
    stmt = select(Strategy).where(Strategy.id == strategy_id)
    result = await session.execute(stmt)
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(404, "Strategy not found")
    await session.delete(strategy)
    await session.commit()
    return {"deleted": True}
