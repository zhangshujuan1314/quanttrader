"""Strategy engine — wraps backtrader Cerebro for backtest + live execution."""
import logging
import multiprocessing
import signal
from dataclasses import dataclass, field
from datetime import date
from typing import Any
import backtrader as bt
import pandas as pd

from app.domain.backtest.metrics import compute_metrics
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    initial_cash: float = settings.default_initial_cash
    commission: float = settings.default_commission
    stamp_duty: float = settings.default_stamp_duty
    slippage: float = settings.default_slippage
    start_date: date | None = None
    end_date: date | None = None


@dataclass
class BacktestOutput:
    equity_curve: list[dict]
    trades: list[dict]
    metrics: dict
    final_value: float
    total_return: float


# ── A-share commission model ──

class AShareCommission(bt.CommInfoBase):
    params = (
        ("commission", 0.00025),
        ("stamp_duty", 0.0005),
        ("min_commission", 5.0),
    )

    def _getcommission(self, size, price, pseudoexec):
        value = abs(size) * price
        comm = max(value * self.p.commission, self.p.min_commission)
        if size < 0:
            comm += value * self.p.stamp_duty
        return comm


# ── Custom analyzer: records individual trades ──

class TradeRecorder(bt.Analyzer):
    """Records each closed trade with entry/exit details for display."""

    def __init__(self):
        self.trades: list[dict] = []

    def notify_trade(self, trade: bt.Trade):
        if trade.isclosed:
            self.trades.append({
                "date": trade.dtclose.strftime("%Y-%m-%d") if trade.dtclose else "",
                "action": "buy" if trade.size > 0 else "sell",
                "price": round(trade.price, 3),
                "size": abs(int(trade.size)),
                "pnl": round(trade.pnl, 2),
                "pnlcomm": round(trade.pnlcomm, 2),
            })

    def get_analysis(self):
        return self.trades


# ── Custom observer: records equity curve ──

class EquityObserver(bt.Observer):
    lines = ("equity",)
    plotinfo = dict(plot=True, subplot=False)

    def next(self):
        self.lines.equity[0] = self._owner.broker.getvalue()


# ── Main backtest entry point ──

def run_backtest(strategy_code: str, data_df: pd.DataFrame,
                 config: BacktestConfig | None = None,
                 strategy_params: dict | None = None,
                 timeout: int = 120) -> BacktestOutput:
    """Run backtest in a subprocess with timeout protection."""
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    p = multiprocessing.Process(
        target=_run_backtest_worker,
        args=(strategy_code, data_df, config, strategy_params, result_queue)
    )
    p.start()
    p.join(timeout=timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        raise TimeoutError(f"Backtest timed out after {timeout}s")
    if result_queue.empty():
        raise RuntimeError("Backtest process failed without result")
    exc, value = result_queue.get()
    if exc is not None:
        raise RuntimeError(f"Backtest error: {exc}\n{value}")
    return value


def _run_backtest_worker(strategy_code: str, data_df: pd.DataFrame,
                         config: BacktestConfig | None,
                         strategy_params: dict | None,
                         queue: multiprocessing.Queue):
    try:
        cfg = config or BacktestConfig()
        cerebro = bt.Cerebro(stdstats=False)  # ponytail: manual observers for cleaner equity

        cerebro.broker.setcash(cfg.initial_cash)
        cerebro.broker.addcommissioninfo(AShareCommission(
            commission=cfg.commission, stamp_duty=cfg.stamp_duty
        ))
        cerebro.broker.set_slippage_perc(cfg.slippage)

        # Feed data
        data_df = data_df.sort_values("trade_date").copy()
        data_feed = bt.feeds.PandasData(
            dataname=data_df.set_index("trade_date"),
            datetime=None, open="open", high="high",
            low="low", close="close", volume="volume", openinterest=-1,
        )
        cerebro.adddata(data_feed)

        # Compile & add user strategy
        strategy_cls = _compile_strategy(strategy_code)
        cerebro.addstrategy(strategy_cls, **(strategy_params or {}))

        # Analyzers
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="ta")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe",
                            riskfreerate=0.015, annualize=True)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(TradeRecorder, _name="recorder")
        cerebro.addobserver(EquityObserver)

        start_value = cerebro.broker.getvalue()
        results = cerebro.run()
        final_value = cerebro.broker.getvalue()

        strat = results[0]
        output = _extract_results(strat, data_df, start_value, final_value)
        queue.put((None, output))
    except Exception as e:
        import traceback
        queue.put((str(e), traceback.format_exc()))


def _compile_strategy(code: str) -> type:
    """Compile user code into a backtrader Strategy subclass."""
    namespace = {"bt": bt, "pd": pd, "__builtins__": __builtins__}
    exec(code, namespace)
    for obj in namespace.values():
        if isinstance(obj, type) and issubclass(obj, bt.Strategy) and obj is not bt.Strategy:
            return obj
    raise ValueError("No backtrader.Strategy subclass found in code")


def _extract_results(strat, data_df: pd.DataFrame,
                     start_value: float, final_value: float) -> BacktestOutput:
    # Trades from custom TradeRecorder
    trade_list = strat.analyzers.recorder.get_analysis()

    # Equity curve from observer
    equity = []
    obs = next((o for o in strat.observers if hasattr(o.lines, 'equity')), None)
    if obs is not None:
        for i, val in enumerate(obs.lines.equity):
            if val and val != 0.0:
                try:
                    d = data_df.iloc[i]["trade_date"]
                    equity.append({"date": str(d), "value": round(float(val), 2)})
                except (IndexError, KeyError):
                    pass

    # Extract backtrader analyzer stats for richer metrics
    ta = strat.analyzers.ta.get_analysis()
    dd = strat.analyzers.drawdown.get_analysis()

    metrics = compute_metrics(
        total_return=(final_value - start_value) / start_value,
        equity_values=[e["value"] for e in equity],
        trades=trade_list,
    )

    # Add backtrader-native metrics when available
    bt_total = ta.get("total", {})
    if bt_total.get("total", 0) > 0:
        metrics["total_trades"] = bt_total["total"]
    metrics["max_drawdown"] = round(dd.get("max", {}).get("drawdown", metrics["max_drawdown"]), 2)

    return BacktestOutput(
        equity_curve=equity,
        trades=trade_list,
        metrics=metrics,
        final_value=round(final_value, 2),
        total_return=(final_value - start_value) / start_value,
    )


# ── Parameter optimization ──

@dataclass
class OptimizeResult:
    best_params: dict
    best_metric: float
    best_metric_name: str
    results: list[dict]  # [{params, metrics}, ...]


def run_optimization(strategy_code: str, data_df: pd.DataFrame,
                     param_grid: dict[str, list],
                     optimize_metric: str = "sharpe_ratio",
                     config: BacktestConfig | None = None,
                     timeout: int = 300) -> OptimizeResult:
    """Grid search over parameter space. Returns best params + full sweep."""
    from itertools import product

    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    all_combos = [dict(zip(param_names, combo)) for combo in product(*param_values)]

    logger.info(f"Optimization: {len(all_combos)} combinations")

    all_results = []
    best = None
    best_val = float("-inf")

    for combo in all_combos:
        try:
            output = run_backtest(strategy_code, data_df, config, combo, timeout=timeout // max(len(all_combos), 1))
            metric_val = output.metrics.get(optimize_metric, 0)
            all_results.append({"params": combo, "metrics": output.metrics})
            if metric_val > best_val:
                best_val = metric_val
                best = combo
        except Exception as e:
            logger.warning(f"Optimization failed for {combo}: {e}")
            all_results.append({"params": combo, "metrics": None, "error": str(e)})

    return OptimizeResult(
        best_params=best or {},
        best_metric=best_val if best else 0,
        best_metric_name=optimize_metric,
        results=all_results,
    )


# ── Built-in strategy templates ──

STRATEGY_TEMPLATES = {
    "ma_cross": {
        "name": "双均线交叉",
        "description": "短期均线上穿长期均线买入，下穿卖出。经典趋势跟踪策略。",
        "code": '''import backtrader as bt

class MACross(bt.Strategy):
    params = (("fast", 5), ("slow", 20))

    def __init__(self):
        self.sma_fast = bt.ind.SMA(period=self.p.fast)
        self.sma_slow = bt.ind.SMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.sma_fast, self.sma_slow)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy(size=100)
        elif self.crossover < 0:
            self.sell(size=100)
''',
        "params": {"fast": 5, "slow": 20},
    },
    "momentum": {
        "name": "动量突破",
        "description": "价格突破N日最高点时买入，跌破N日最低点时卖出。",
        "code": '''import backtrader as bt

class MomentumBreakout(bt.Strategy):
    params = (("period", 20),)

    def __init__(self):
        self.highest = bt.ind.Highest(self.data.high, period=self.p.period)
        self.lowest = bt.ind.Lowest(self.data.low, period=self.p.period)

    def next(self):
        if not self.position:
            if self.data.close[0] > self.highest[-1]:
                self.buy(size=100)
        else:
            if self.data.close[0] < self.lowest[-1]:
                self.sell(size=100)
''',
        "params": {"period": 20},
    },
    "grid_trading": {
        "name": "网格交易",
        "description": "在设定价格区间内按固定间距分批买入卖出，适合震荡市。",
        "code": '''import backtrader as bt

class GridTrading(bt.Strategy):
    params = (("grid_pct", 0.02), ("base_price", None))

    def __init__(self):
        self.last_buy_price = self.p.base_price or self.data.close[0]

    def next(self):
        price = self.data.close[0]
        if not self.position:
            if price <= self.last_buy_price * (1 - self.p.grid_pct):
                self.buy(size=100)
                self.last_buy_price = price
        else:
            if price >= self.last_buy_price * (1 + self.p.grid_pct):
                self.sell(size=100)
                self.last_buy_price = price
''',
        "params": {"grid_pct": 0.02},
    },
}
