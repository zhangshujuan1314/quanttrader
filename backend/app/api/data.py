from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.database import get_session
from app.infrastructure.persistence.models import StockInfo, MarketDaily
from app.infrastructure.data.sync_service import DataSyncService

router = APIRouter(tags=["data"])


@router.get("/symbols")
async def list_symbols(q: str = Query(default="", description="Search by code or name"),
                       session: AsyncSession = Depends(get_session)):
    stmt = select(StockInfo.ts_code, StockInfo.name, StockInfo.market)
    if q:
        stmt = stmt.where(
            (StockInfo.ts_code.ilike(f"%{q}%")) |
            (StockInfo.name.ilike(f"%{q}%"))
        )
    stmt = stmt.limit(100)
    result = await session.execute(stmt)
    rows = result.fetchall()
    return [{"ts_code": r[0], "name": r[1], "market": r[2]} for r in rows]


@router.get("/kline")
async def get_kline(ts_code: str = Query(...),
                    start: str = Query(default="2020-01-01"),
                    end: str = Query(default_factory=lambda: date.today().isoformat()),
                    session: AsyncSession = Depends(get_session)):
    stmt = select(MarketDaily).where(
        MarketDaily.ts_code == ts_code,
        MarketDaily.trade_date >= start,
        MarketDaily.trade_date <= end,
    ).order_by(MarketDaily.trade_date.asc())
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [{
        "ts_code": r.ts_code, "trade_date": str(r.trade_date),
        "open": r.open, "high": r.high, "low": r.low,
        "close": r.close, "volume": r.volume, "amount": r.amount,
        "adj_factor": r.adj_factor,
    } for r in rows]


@router.post("/sync/stocks")
async def sync_stocks(session: AsyncSession = Depends(get_session)):
    svc = DataSyncService()
    count = await svc.sync_stock_list(session)
    return {"synced": count}


@router.post("/sync/daily")
async def sync_daily(symbols: list[str] | None = None,
                     days_back: int = Query(default=365),
                     session: AsyncSession = Depends(get_session)):
    svc = DataSyncService()
    count = await svc.sync_daily(session, symbols=symbols, days_back=days_back)
    return {"synced": count}
