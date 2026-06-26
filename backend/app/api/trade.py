"""Trade API — paper trading execution for V1.0."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.domain.trade.paper_broker import PaperBroker, OrderAction, OrderStatus
from app.domain.risk.engine import RiskEngine, RiskConfig, OrderRequest, AccountState

router = APIRouter(tags=["trade"])

# ponytail: single global broker per process for MVP
# later: per-user broker instances with Redis state
_broker = PaperBroker(initial_cash=100000.0)
_risk_engine = RiskEngine()


class TradeRequest(BaseModel):
    symbol: str
    action: str  # buy / sell
    quantity: int
    limit_price: float | None = None


class PriceUpdate(BaseModel):
    symbol: str
    price: float


@router.get("/account")
async def get_account():
    return _broker.get_account_summary()


@router.post("/order")
async def place_order(req: TradeRequest):
    action = OrderAction.BUY if req.action == "buy" else OrderAction.SELL

    # Risk check
    account_state = AccountState(
        total_value=_broker.account.total_value,
        cash=_broker.account.cash,
        positions={s: p.market_value for s, p in _broker.account.positions.items()},
    )
    order_req = OrderRequest(
        symbol=req.symbol, action=req.action,
        quantity=req.quantity, price=req.limit_price or _broker._current_prices.get(req.symbol, 0),
        order_value=req.quantity * (req.limit_price or _broker._current_prices.get(req.symbol, 0)),
    )
    checks = _risk_engine.check_order(order_req, account_state)
    blocked = [c for c in checks if not c.passed and c.level.value in ("block", "circuit_break")]

    if blocked:
        return {
            "status": "rejected",
            "reason": blocked[0].message,
            "checks": [{"name": c.name, "passed": c.passed, "message": c.message} for c in checks],
        }

    order = _broker.submit_order(req.symbol, action, req.quantity, req.limit_price)
    return {
        "order_id": order.id,
        "status": order.status.value,
        "filled_price": order.filled_price if order.status == OrderStatus.FILLED else None,
        "commission": order.commission,
    }


@router.post("/price")
async def update_price(req: PriceUpdate):
    """Update current price (for paper trading mark-to-market)."""
    _broker.update_price(req.symbol, req.price)
    return {"symbol": req.symbol, "price": req.price}


@router.get("/orders")
async def list_orders():
    return [{
        "id": o.id, "symbol": o.symbol, "action": o.action.value,
        "quantity": o.quantity, "status": o.status.value,
        "filled_qty": o.filled_qty, "filled_price": o.filled_price,
        "commission": o.commission, "created_at": o.created_at,
    } for o in _broker.account.orders[-50:]]


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str):
    ok = _broker.cancel_order(order_id)
    if not ok:
        raise HTTPException(404, "Order not found or already filled/cancelled")
    return {"cancelled": True}


@router.get("/risk/status")
async def risk_status():
    return {
        "circuit_broken": _risk_engine.config.circuit_broken,
        "rules": {
            "max_daily_loss_pct": _risk_engine.config.max_daily_loss_pct,
            "max_position_pct": _risk_engine.config.max_position_pct,
            "single_stock_limit_pct": _risk_engine.config.single_stock_limit_pct,
            "stop_loss_pct": _risk_engine.config.stop_loss_pct,
        },
    }


@router.post("/risk/reset")
async def reset_risk():
    _risk_engine.reset_daily()
    return {"reset": True}
