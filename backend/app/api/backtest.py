import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from app.infrastructure.persistence.database import get_session
from app.infrastructure.persistence.models import Strategy, BacktestResult, MarketDaily
from app.domain.strategy.safe_engine import run_backtest, run_optimization, BacktestConfig
from app.domain.backtest.monte_carlo import run_monte_carlo, run_stress_test
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["backtest"])


class BacktestRequest(BaseModel):
    strategy_id: str | None = None
    strategy_code: str | None = None       # direct code (trusted-only unless unsafe execution is explicitly enabled)
    strategy_params: dict = {}
    ts_code: str                           # e.g. "000001.SZ"
    start_date: str                        # "2022-01-01"
    end_date: str                          # "2024-12-31"
    initial_cash: float = settings.default_initial_cash
    commission: float = settings.default_commission


class BacktestResponse(BaseModel):
    id: str
    status: str
    metrics: dict | None = None
    equity_curve: list[dict] | None = None
    trades: list[dict] | None = None


@router.post("/run", response_model=BacktestResponse)
async def run_backtest_endpoint(req: BacktestRequest,
                                session: AsyncSession = Depends(get_session)):
    """Run a backtest and return results."""
    # Resolve strategy code
    if req.strategy_id:
        stmt = select(Strategy).where(Strategy.id == req.strategy_id)
        result = await session.execute(stmt)
        strat = result.scalar_one_or_none()
        if not strat:
            raise HTTPException(404, "Strategy not found")
        code = strat.code
        strategy_id = req.strategy_id
    elif req.strategy_code:
        code = req.strategy_code
        strategy_id = None
    else:
        raise HTTPException(400, "Must provide strategy_id or strategy_code")

    # Load market data
    stmt = select(MarketDaily).where(
        MarketDaily.ts_code == req.ts_code,
        MarketDaily.trade_date >= req.start_date,
        MarketDaily.trade_date <= req.end_date,
    ).order_by(MarketDaily.trade_date.asc())
    result = await session.execute(stmt)
    rows = result.scalars().all()

    if len(rows) < 30:
        raise HTTPException(400, f"Insufficient data: only {len(rows)} records. Need at least 30 trading days.")

    df = pd.DataFrame([{
        "trade_date": r.trade_date, "open": r.open, "high": r.high,
        "low": r.low, "close": r.close, "volume": r.volume,
    } for r in rows])

    # Run backtest
    config = BacktestConfig(
        initial_cash=req.initial_cash, commission=req.commission,
        start_date=date.fromisoformat(req.start_date),
        end_date=date.fromisoformat(req.end_date),
    )
    try:
        output = run_backtest(code, df, config, req.strategy_params)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except TimeoutError as e:
        raise HTTPException(408, str(e))
    except Exception as e:
        logger.exception("Backtest failed")
        raise HTTPException(500, f"Backtest error: {e}")

    # Persist result
    bt_result = BacktestResult(
        strategy_id=strategy_id or "direct-run",
        ts_code=req.ts_code,
        start_date=req.start_date,
        end_date=req.end_date,
        initial_cash=req.initial_cash,
        final_value=output.final_value,
        total_return=output.metrics["total_return"],
        annual_return=output.metrics["annual_return"],
        max_drawdown=output.metrics["max_drawdown"],
        sharpe_ratio=output.metrics["sharpe_ratio"],
        win_rate=output.metrics["win_rate"],
        total_trades=output.metrics["total_trades"],
        equity_curve=output.equity_curve,
        trades=output.trades,
        config=req.model_dump(),
        status="completed",
    )
    session.add(bt_result)
    await session.commit()
    await session.refresh(bt_result)

    return BacktestResponse(
        id=bt_result.id, status="completed",
        metrics=output.metrics, equity_curve=output.equity_curve,
        trades=output.trades,
    )


@router.get("/results")
async def list_results(session: AsyncSession = Depends(get_session)):
    stmt = select(BacktestResult).order_by(BacktestResult.created_at.desc()).limit(50)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [{
        "id": str(r.id), "strategy_id": str(r.strategy_id),
        "ts_code": r.ts_code, "start_date": str(r.start_date),
        "end_date": str(r.end_date), "total_return": r.total_return,
        "annual_return": r.annual_return, "max_drawdown": r.max_drawdown,
        "sharpe_ratio": r.sharpe_ratio, "total_trades": r.total_trades,
        "status": r.status, "created_at": str(r.created_at),
    } for r in rows]


@router.get("/results/{result_id}")
async def get_result(result_id: str, session: AsyncSession = Depends(get_session)):
    stmt = select(BacktestResult).where(BacktestResult.id == result_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Result not found")
    return {
        "id": str(row.id), "strategy_id": str(row.strategy_id),
        "ts_code": row.ts_code, "metrics": {
            "total_return": row.total_return, "annual_return": row.annual_return,
            "max_drawdown": row.max_drawdown, "sharpe_ratio": row.sharpe_ratio,
            "win_rate": row.win_rate, "total_trades": row.total_trades,
        },
        "equity_curve": row.equity_curve, "trades": row.trades,
        "created_at": str(row.created_at),
    }


# ── Parameter Optimization ──

class OptimizeRequest(BaseModel):
    strategy_id: str | None = None
    strategy_code: str | None = None
    ts_code: str
    start_date: str
    end_date: str
    param_grid: dict[str, list]  # e.g. {"fast": [3,5,10], "slow": [15,20,30]}
    optimize_metric: str = "sharpe_ratio"
    initial_cash: float = settings.default_initial_cash


@router.post("/optimize")
async def optimize_strategy(req: OptimizeRequest,
                            session: AsyncSession = Depends(get_session)):
    """Grid search over parameter space."""
    if req.strategy_id:
        stmt = select(Strategy).where(Strategy.id == req.strategy_id)
        result = await session.execute(stmt)
        strat = result.scalar_one_or_none()
        if not strat:
            raise HTTPException(404, "Strategy not found")
        code = strat.code
    elif req.strategy_code:
        code = req.strategy_code
    else:
        raise HTTPException(400, "Must provide strategy_id or strategy_code")

    # Load data
    stmt = select(MarketDaily).where(
        MarketDaily.ts_code == req.ts_code,
        MarketDaily.trade_date >= req.start_date,
        MarketDaily.trade_date <= req.end_date,
    ).order_by(MarketDaily.trade_date.asc())
    result = await session.execute(stmt)
    rows = result.scalars().all()
    if len(rows) < 30:
        raise HTTPException(400, f"Insufficient data: {len(rows)} records")

    df = pd.DataFrame([{
        "trade_date": r.trade_date, "open": r.open, "high": r.high,
        "low": r.low, "close": r.close, "volume": r.volume,
    } for r in rows])

    config = BacktestConfig(initial_cash=req.initial_cash)
    try:
        opt = run_optimization(code, df, req.param_grid, req.optimize_metric, config)
    except PermissionError as e:
        raise HTTPException(403, str(e))

    return {
        "best_params": opt.best_params,
        "best_metric": opt.best_metric,
        "best_metric_name": opt.best_metric_name,
        "total_combinations": len(opt.results),
        "results": opt.results,
    }


# ── Compare multiple backtests ──

class CompareRequest(BaseModel):
    result_ids: list[str]


@router.post("/compare")
async def compare_backtests(req: CompareRequest,
                            session: AsyncSession = Depends(get_session)):
    """Compare multiple backtest results side by side."""
    stmt = select(BacktestResult).where(BacktestResult.id.in_(req.result_ids))
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [{
        "id": str(r.id), "ts_code": r.ts_code,
        "total_return": r.total_return, "annual_return": r.annual_return,
        "max_drawdown": r.max_drawdown, "sharpe_ratio": r.sharpe_ratio,
        "win_rate": r.win_rate, "total_trades": r.total_trades,
        "equity_curve": r.equity_curve,
    } for r in rows]


# ── Monte Carlo & Stress Test ──

@router.get("/results/{result_id}/monte-carlo")
async def monte_carlo_analysis(result_id: str,
                               n_simulations: int = 500,
                               method: str = "resample",
                               session: AsyncSession = Depends(get_session)):
    """Run Monte Carlo simulation on a backtest result."""
    stmt = select(BacktestResult).where(BacktestResult.id == result_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Result not found")

    mc = run_monte_carlo(
        trades=row.trades or [],
        equity_curve=row.equity_curve or [],
        initial_cash=row.initial_cash,
        n_simulations=n_simulations,
        method=method,
    )

    # Build histogram data for frontend
    dist = mc.return_distribution
    bins = 30
    if dist:
        hist_min, hist_max = min(dist), max(dist)
        bin_width = (hist_max - hist_min) / bins if hist_max != hist_min else 1
        histogram = []
        for i in range(bins):
            low = hist_min + i * bin_width
            high = low + bin_width
            count = sum(1 for x in dist if low <= x < high)
            histogram.append({"bin": round((low + high) / 2, 2), "count": count})
    else:
        histogram = []

    return {
        "simulations": mc.simulations,
        "method": mc.method,
        "original_return": mc.original_return,
        "mean_return": mc.mean_return,
        "median_return": mc.median_return,
        "p5_return": mc.p5_return,
        "p95_return": mc.p95_return,
        "std_return": mc.std_return,
        "prob_loss": mc.prob_loss,
        "histogram": histogram,
    }


@router.get("/results/{result_id}/stress-test")
async def stress_test_analysis(result_id: str,
                               session: AsyncSession = Depends(get_session)):
    """Run stress test scenarios on a backtest result."""
    stmt = select(BacktestResult).where(BacktestResult.id == result_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Result not found")

    scenarios = run_stress_test(
        equity_curve=row.equity_curve or [],
        initial_cash=row.initial_cash,
    )
    return {"scenarios": scenarios}
