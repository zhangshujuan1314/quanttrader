"""Monte Carlo simulation for backtest robustness analysis.

ponytail: bootstrap resampling of trade returns + random permutation of trade order.
Two methods:
1. Resample: randomly sample trades with replacement → distribution of final returns
2. Permute: shuffle trade order → see if timing luck matters
"""
import random
import numpy as np
from dataclasses import dataclass, field


@dataclass
class MonteCarloResult:
    simulations: int
    method: str  # "resample" or "permute"
    original_return: float  # annualized %
    mean_return: float
    median_return: float
    p5_return: float       # 5th percentile (worst case)
    p95_return: float      # 95th percentile (best case)
    std_return: float
    prob_loss: float       # P(final return < 0)
    return_distribution: list[float] = field(default_factory=list)
    metrics_distribution: dict[str, list[float]] = field(default_factory=dict)


def run_monte_carlo(trades: list[dict], equity_curve: list[dict],
                    initial_cash: float = 100000,
                    n_simulations: int = 500,
                    method: str = "resample") -> MonteCarloResult:
    """Run Monte Carlo simulation on backtest results.

    Args:
        trades: list of {pnl, date, ...} dicts
        equity_curve: list of {date, value} dicts
        initial_cash: starting capital
        n_simulations: number of simulation runs
        method: "resample" (bootstrap PnLs) or "permute" (shuffle trade order)
    """
    if not trades or len(trades) < 5:
        return MonteCarloResult(
            simulations=0, method=method, original_return=0,
            mean_return=0, median_return=0, p5_return=0, p95_return=0,
            std_return=0, prob_loss=0,
        )

    # Extract per-trade PnL in absolute terms
    trade_pnls = [t.get("pnl", 0) for t in trades]

    # Compute original annualized return
    if len(equity_curve) >= 2:
        n_days = len(equity_curve)
        final_val = equity_curve[-1]["value"]
        total_ret = (final_val - initial_cash) / initial_cash
        original_return = ((1 + total_ret) ** (252 / n_days) - 1) * 100
    else:
        original_return = 0.0

    final_returns = []
    for _ in range(n_simulations):
        if method == "resample":
            # Bootstrap: sample trades with replacement
            sampled_pnls = np.random.choice(trade_pnls, size=len(trade_pnls), replace=True)
            sim_return = sum(sampled_pnls)
        else:
            # Permute: shuffle trade order, recompute equity with drawdown constraints
            shuffled = trade_pnls.copy()
            random.shuffle(shuffled)
            # Simulate equity path: if equity goes below 0, stop
            equity = initial_cash
            for pnl in shuffled:
                equity += pnl
                if equity <= 0:
                    break
            sim_return = equity - initial_cash

        final_returns.append(sim_return)

    returns_arr = np.array(final_returns)
    return_pcts = returns_arr / initial_cash * 100

    prob_loss = float(np.mean(return_pcts < 0))

    return MonteCarloResult(
        simulations=n_simulations, method=method,
        original_return=round(original_return, 2),
        mean_return=round(float(np.mean(return_pcts)), 2),
        median_return=round(float(np.median(return_pcts)), 2),
        p5_return=round(float(np.percentile(return_pcts, 5)), 2),
        p95_return=round(float(np.percentile(return_pcts, 95)), 2),
        std_return=round(float(np.std(return_pcts)), 2),
        prob_loss=round(prob_loss * 100, 1),
        return_distribution=[round(float(x), 2) for x in return_pcts.tolist()],
    )


def run_stress_test(equity_curve: list[dict], initial_cash: float,
                    scenarios: list[dict] | None = None) -> list[dict]:
    """Run stress scenarios on backtest equity curve.

    Default scenarios:
    - Market crash: -15% one-day drop
    - Correction: -30% over 20 days
    - Stagflation: sideways +5%/-5% over 60 days
    """
    if scenarios is None:
        scenarios = [
            {"name": "市场暴跌 (-15%)", "shock": -0.15, "duration": 1},
            {"name": "持续阴跌 (-30%/20天)", "shock": -0.30, "duration": 20},
            {"name": "震荡横盘 (±5%/60天)", "shock": 0.0, "duration": 60, "volatility": 0.05},
        ]

    if not equity_curve or len(equity_curve) < 10:
        return [{"scenario": s["name"], "error": "insufficient data"} for s in scenarios]

    results = []
    final_value = equity_curve[-1]["value"]

    for scenario in scenarios:
        shocked_value = final_value
        if "volatility" in scenario:
            # Random walk with bounded volatility
            np.random.seed(42)
            for _ in range(scenario["duration"]):
                shocked_value *= (1 + np.random.uniform(-scenario["volatility"], scenario["volatility"]))
        else:
            # Apply linear shock over duration
            daily_shock = scenario["shock"] / scenario["duration"]
            for _ in range(scenario["duration"]):
                shocked_value *= (1 + daily_shock)

        impact_pct = (shocked_value - final_value) / final_value * 100
        survived = shocked_value > initial_cash * 0.5  # > 50% of initial capital

        results.append({
            "scenario": scenario["name"],
            "final_value": round(shocked_value, 2),
            "impact_pct": round(impact_pct, 2),
            "survived": survived,
        })

    return results
