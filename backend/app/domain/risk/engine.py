"""Risk control engine — pre-trade checks, circuit breakers, stop-loss.

ponytail: risk rules are a simple ordered list of if-else checks.
No rule engine DSL needed for MVP/V1. Add expression engine if rules get complex.
"""
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCK = "block"       # reject this order
    CIRCUIT_BREAK = "circuit_break"  # halt all trading for the day


@dataclass
class RiskCheck:
    name: str
    level: RiskLevel
    passed: bool
    message: str = ""


@dataclass
class AccountState:
    """Current account snapshot for risk evaluation."""
    total_value: float
    cash: float
    positions: dict[str, float] = field(default_factory=dict)  # symbol -> market_value
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    consecutive_loss_days: int = 0


@dataclass
class OrderRequest:
    symbol: str
    action: str  # buy / sell
    quantity: int
    price: float
    order_value: float  # quantity * price


@dataclass
class RiskConfig:
    # Account-level
    max_daily_loss_pct: float = -0.05       # circuit break if daily loss > 5%
    max_position_pct: float = 0.80          # max total position / total value
    max_consecutive_loss_days: int = 3      # pause after 3 losing days

    # Stock-level
    single_stock_limit_pct: float = 0.20    # single stock max position / total value
    stop_loss_pct: float = -0.08            # auto close if unrealized pnl < -8%

    # Order-level
    max_order_freq_per_sec: int = 3
    max_single_order_pct: float = 0.10      # single order max / total value

    # Blacklist
    blocked_symbols: set[str] = field(default_factory=set)  # ST stocks, etc.

    # ponytail: add more rules by appending to self.rules list
    def __post_init__(self):
        self.circuit_broken: bool = False
        self.last_order_times: list[float] = []  # timestamps for rate limiting


class RiskEngine:
    """Evaluates orders against risk rules. Strategy produces signals;
    RiskEngine decides if they become orders."""

    def __init__(self, config: RiskConfig | None = None):
        self.config = config or RiskConfig()

    def check_order(self, order: OrderRequest, account: AccountState) -> list[RiskCheck]:
        """Run all pre-trade checks. Returns list of checks (all must pass)."""
        checks: list[RiskCheck] = []

        # 1. Circuit breaker (highest priority)
        if self.config.circuit_broken:
            checks.append(RiskCheck("熔断已触发", RiskLevel.CIRCUIT_BREAK, False,
                                    "当日交易已被熔断，请明天再试"))
            return checks

        # 2. Daily loss limit
        if account.daily_pnl_pct <= self.config.max_daily_loss_pct:
            self.config.circuit_broken = True
            checks.append(RiskCheck("日亏损熔断", RiskLevel.CIRCUIT_BREAK, False,
                                    f"日亏损已达{account.daily_pnl_pct:.2%}，触发熔断"))

        # 3. Consecutive loss days
        if account.consecutive_loss_days >= self.config.max_consecutive_loss_days:
            checks.append(RiskCheck("连续亏损暂停", RiskLevel.CIRCUIT_BREAK, False,
                                    f"连续{account.consecutive_loss_days}天亏损，暂停交易"))

        # 4. Blacklisted symbols
        if order.symbol in self.config.blocked_symbols:
            checks.append(RiskCheck("禁止交易标的", RiskLevel.BLOCK, False,
                                    f"{order.symbol} 在禁止交易名单中"))

        # 5. Max position limit
        current_position_value = sum(account.positions.values())
        proposed_value = current_position_value + (order.order_value if order.action == "buy" else -order.order_value)
        if proposed_value / account.total_value > self.config.max_position_pct:
            checks.append(RiskCheck("总仓位超限", RiskLevel.BLOCK, False,
                                    f"仓位将达{proposed_value/account.total_value:.1%}，超过{self.config.max_position_pct:.0%}上限"))

        # 6. Single stock limit
        stock_value = account.positions.get(order.symbol, 0)
        after_value = stock_value + (order.order_value if order.action == "buy" else -order.order_value)
        if after_value / account.total_value > self.config.single_stock_limit_pct:
            checks.append(RiskCheck("单票仓位超限", RiskLevel.BLOCK, False,
                                    f"{order.symbol}仓位将达{after_value/account.total_value:.1%}，超过{self.config.single_stock_limit_pct:.0%}上限"))

        # 7. Single order size limit
        if order.order_value / account.total_value > self.config.max_single_order_pct:
            checks.append(RiskCheck("单笔订单超限", RiskLevel.WARNING, False,
                                    f"单笔金额达{order.order_value/account.total_value:.1%}，建议分批"))

        # 8. Rate limiting (ponytail: simple timestamp list)
        import time
        now = time.time()
        self.config.last_order_times = [t for t in self.config.last_order_times if t > now - 1.0]
        if len(self.config.last_order_times) >= self.config.max_order_freq_per_sec:
            checks.append(RiskCheck("下单频率超限", RiskLevel.BLOCK, False,
                                    f"每秒最多{self.config.max_order_freq_per_sec}笔"))
        self.config.last_order_times.append(now)

        # If no explicit fails, all passed
        if not checks:
            checks.append(RiskCheck("风控通过", RiskLevel.INFO, True, "所有检查通过"))

        return checks

    def check_stop_loss(self, symbol: str, entry_price: float,
                        current_price: float, position_size: int) -> RiskCheck:
        """Check if position should be stopped out."""
        pnl_pct = (current_price - entry_price) / entry_price
        if pnl_pct <= self.config.stop_loss_pct:
            return RiskCheck("止损触发", RiskLevel.BLOCK, False,
                             f"{symbol} 亏损{pnl_pct:.2%}，触发{self.config.stop_loss_pct:.0%}止损")
        return RiskCheck("止损检查", RiskLevel.INFO, True, "未触发止损")

    def reset_daily(self):
        """Reset daily circuit breaker at start of new trading day."""
        self.config.circuit_broken = False
        self.config.last_order_times.clear()
