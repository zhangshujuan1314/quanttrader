"""Performance metrics computation. Uses empyrical where possible, falls back to numpy."""
import math
import numpy as np


def compute_metrics(total_return: float, equity_values: list[float],
                    trades: list[dict]) -> dict:
    """Compute key performance metrics from backtest results."""

    # Annual return
    returns = np.diff(equity_values) / equity_values[:-1] if len(equity_values) > 1 else np.array([])
    n_days = len(equity_values)
    annual_return = (1 + total_return) ** (252 / max(n_days, 1)) - 1

    # Max drawdown
    peaks = np.maximum.accumulate(equity_values)
    drawdowns = (np.array(equity_values) - peaks) / peaks
    max_drawdown = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

    # Sharpe ratio (annualized, risk-free=1.5%)
    if len(returns) > 1 and returns.std() > 0:
        excess = returns - 0.015 / 252
        sharpe = float(excess.mean() / returns.std() * math.sqrt(252)) if returns.std() > 0 else 0.0
    else:
        sharpe = 0.0

    # Calmar ratio
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

    # Win rate & profit factor
    winning = [t for t in trades if t.get("pnl", 0) > 0]
    losing = [t for t in trades if t.get("pnl", 0) < 0]
    win_rate = len(winning) / len(trades) if trades else 0.0

    total_win = sum(t.get("pnl", 0) for t in winning)
    total_loss = abs(sum(t.get("pnl", 0) for t in losing))
    profit_factor = total_win / total_loss if total_loss > 0 else float("inf")

    return {
        "total_return": round(total_return * 100, 2),
        "annual_return": round(annual_return * 100, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "calmar_ratio": round(calmar, 3),
        "win_rate": round(win_rate * 100, 2),
        "profit_factor": round(min(profit_factor, 999), 2),
        "total_trades": len(trades),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
    }
