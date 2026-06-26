"""Paper trading broker — simulates order execution with slippage and fees.

ponytail: simple matching engine that fills at next bar's open.
Tracks orders, positions, PnL in memory. V1.0 for strategy validation.
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    CREATED = "created"
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class OrderAction(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    symbol: str = ""
    action: OrderAction = OrderAction.BUY
    quantity: int = 0
    limit_price: float | None = None  # None = market order
    status: OrderStatus = OrderStatus.CREATED
    filled_qty: int = 0
    filled_price: float = 0.0
    commission: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    filled_at: str = ""


@dataclass
class Position:
    symbol: str
    quantity: int
    avg_cost: float
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


@dataclass
class Account:
    initial_cash: float
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    orders: list[Order] = field(default_factory=list)
    trade_history: list[dict] = field(default_factory=list)

    @property
    def total_value(self) -> float:
        position_value = sum(p.market_value for p in self.positions.values())
        return self.cash + position_value

    @property
    def total_pnl(self) -> float:
        return self.total_value - self.initial_cash

    @property
    def total_pnl_pct(self) -> float:
        return self.total_pnl / self.initial_cash if self.initial_cash else 0


class PaperBroker:
    """Simulated broker for strategy validation before live trading."""

    def __init__(self, initial_cash: float = 100000.0,
                 commission_rate: float = 0.00025,
                 stamp_duty: float = 0.0005,
                 slippage_pct: float = 0.001):
        self.account = Account(initial_cash=initial_cash, cash=initial_cash)
        self.commission_rate = commission_rate
        self.stamp_duty = stamp_duty
        self.slippage_pct = slippage_pct
        self._current_prices: dict[str, float] = {}

    def update_price(self, symbol: str, price: float):
        """Update last known price for mark-to-market."""
        self._current_prices[symbol] = price
        if symbol in self.account.positions:
            pos = self.account.positions[symbol]
            pos.market_value = pos.quantity * price
            pos.unrealized_pnl = (price - pos.avg_cost) * pos.quantity
            pos.unrealized_pnl_pct = (price - pos.avg_cost) / pos.avg_cost if pos.avg_cost else 0

    def submit_order(self, symbol: str, action: OrderAction,
                     quantity: int, limit_price: float | None = None) -> Order:
        """Create and submit an order. Fills immediately at market or at limit."""
        order = Order(symbol=symbol, action=action, quantity=quantity,
                      limit_price=limit_price, status=OrderStatus.SUBMITTED)
        self.account.orders.append(order)

        current_price = self._current_prices.get(symbol)
        if current_price is None:
            order.status = OrderStatus.REJECTED
            return order

        fill_price = limit_price if limit_price else current_price

        # Apply slippage
        slippage = fill_price * (self.slippage_pct if action == OrderAction.BUY else -self.slippage_pct)
        fill_price += slippage

        # Calculate costs
        trade_value = quantity * fill_price
        commission = max(trade_value * self.commission_rate, 5.0)
        tax = trade_value * self.stamp_duty if action == OrderAction.SELL else 0

        if action == OrderAction.BUY:
            cost = trade_value + commission
            if cost > self.account.cash:
                order.status = OrderStatus.REJECTED
                return order
            self.account.cash -= cost
            self._update_position(symbol, quantity, fill_price)
        else:
            pos = self.account.positions.get(symbol)
            if not pos or pos.quantity < quantity:
                order.status = OrderStatus.REJECTED
                return order
            self.account.cash += trade_value - commission - tax
            self._update_position(symbol, -quantity, fill_price)

        order.status = OrderStatus.FILLED
        order.filled_qty = quantity
        order.filled_price = fill_price
        order.commission = commission
        order.filled_at = datetime.now().isoformat()

        trade_record = {
            "order_id": order.id, "symbol": symbol, "action": action.value,
            "quantity": quantity, "price": round(fill_price, 3),
            "commission": round(commission, 2),
            "filled_at": order.filled_at,
        }
        self.account.trade_history.append(trade_record)
        return order

    def _update_position(self, symbol: str, delta: int, price: float):
        if symbol not in self.account.positions:
            self.account.positions[symbol] = Position(symbol=symbol, quantity=0, avg_cost=0)
        pos = self.account.positions[symbol]
        if delta > 0:
            total_cost = pos.avg_cost * pos.quantity + price * delta
            pos.quantity += delta
            pos.avg_cost = total_cost / pos.quantity if pos.quantity > 0 else 0
        else:
            pos.quantity += delta  # delta is negative
            if pos.quantity <= 0:
                del self.account.positions[symbol]
                return
        pos.market_value = pos.quantity * price

    def cancel_order(self, order_id: str) -> bool:
        for o in self.account.orders:
            if o.id == order_id and o.status in (OrderStatus.CREATED, OrderStatus.SUBMITTED):
                o.status = OrderStatus.CANCELLED
                return True
        return False

    def get_account_summary(self) -> dict:
        return {
            "initial_cash": self.account.initial_cash,
            "cash": round(self.account.cash, 2),
            "total_value": round(self.account.total_value, 2),
            "total_pnl": round(self.account.total_pnl, 2),
            "total_pnl_pct": round(self.account.total_pnl_pct * 100, 2),
            "positions": {
                sym: {
                    "quantity": p.quantity, "avg_cost": round(p.avg_cost, 3),
                    "market_value": round(p.market_value, 2),
                    "unrealized_pnl": round(p.unrealized_pnl, 2),
                    "unrealized_pnl_pct": round(p.unrealized_pnl_pct * 100, 2),
                }
                for sym, p in self.account.positions.items()
            },
            "pending_orders": len([o for o in self.account.orders
                                   if o.status in (OrderStatus.CREATED, OrderStatus.SUBMITTED)]),
            "filled_orders": len([o for o in self.account.orders
                                  if o.status == OrderStatus.FILLED]),
        }
