"""Data sync service — pulls A-share daily data into PostgreSQL."""
import logging
from datetime import date, timedelta
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.data.akshare_adapter import AkshareAdapter
from app.infrastructure.persistence.models import MarketDaily, StockInfo

logger = logging.getLogger(__name__)


class DataSyncService:
    def __init__(self, adapter: AkshareAdapter | None = None):
        self.adapter = adapter or AkshareAdapter()

    async def sync_stock_list(self, session: AsyncSession) -> int:
        df = self.adapter.fetch_stock_list()
        count = 0
        for _, row in df.iterrows():
            stmt = insert(StockInfo).values(
                ts_code=row["ts_code"],
                name=row.get("name", ""),
                market=self._guess_market(row["ts_code"]),
            ).on_conflict_do_update(
                index_elements=["ts_code"],
                set_={"name": row.get("name", "")}
            )
            await session.execute(stmt)
            count += 1
        await session.commit()
        logger.info(f"Synced {count} stocks")
        return count

    async def sync_daily(self, session: AsyncSession, symbols: list[str] | None = None,
                         days_back: int = 365, end_date: date | None = None):
        end = end_date or date.today()
        start = end - timedelta(days=days_back)

        if symbols is None:
            # Get all symbols from DB
            from sqlalchemy import select
            result = await session.execute(select(StockInfo.ts_code))
            symbols = [r[0] for r in result.fetchall()]

        total = 0
        for symbol in symbols:
            df = self.adapter.fetch_daily(symbol, start, end)
            if df.empty:
                continue
            for _, row in df.iterrows():
                stmt = insert(MarketDaily).values(
                    ts_code=row["ts_code"],
                    trade_date=row["trade_date"],
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                    amount=float(row.get("amount", 0) or 0),
                    adj_factor=float(row.get("adj_factor", 1.0)),
                ).on_conflict_do_nothing()
                await session.execute(stmt)
            total += len(df)

        await session.commit()
        logger.info(f"Synced {total} daily records for {len(symbols)} symbols")
        return total

    @staticmethod
    def _guess_market(code: str) -> str:
        if code.startswith("60") or code.startswith("68"):
            return "SH"
        elif code.startswith("00") or code.startswith("30"):
            return "SZ"
        elif code.startswith("8") or code.startswith("4"):
            return "BJ"
        return "UNKNOWN"
