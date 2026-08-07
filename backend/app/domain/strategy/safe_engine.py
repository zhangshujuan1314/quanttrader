"""Fail-closed API-facing wrapper around the Python strategy engine.

The underlying engine executes strategy source with ``exec`` and is therefore
only safe for trusted code. This module keeps built-in repository templates
working while refusing arbitrary custom source unless an operator explicitly
opts into trusted-code execution with ``QT_ALLOW_UNSAFE_STRATEGY_EXEC=true``.
"""
from app.config import settings
from app.domain.strategy.engine import (
    BacktestConfig,
    BacktestOutput,
    OptimizeResult,
    STRATEGY_TEMPLATES,
    run_backtest as _run_backtest,
    run_optimization as _run_optimization,
)


def is_builtin_strategy_code(code: str) -> bool:
    candidate = code.strip()
    return any(template["code"].strip() == candidate for template in STRATEGY_TEMPLATES.values())


def ensure_strategy_code_allowed(code: str) -> None:
    if is_builtin_strategy_code(code):
        return
    if settings.allow_unsafe_strategy_exec:
        return
    raise PermissionError(
        "Custom Python strategy execution is disabled because strategy source is arbitrary code. "
        "Use a built-in template, or set QT_ALLOW_UNSAFE_STRATEGY_EXEC=true only in a trusted isolated environment."
    )


def run_backtest(*args, **kwargs) -> BacktestOutput:
    strategy_code = args[0] if args else kwargs.get("strategy_code")
    if not isinstance(strategy_code, str):
        raise TypeError("strategy_code must be a string")
    ensure_strategy_code_allowed(strategy_code)
    return _run_backtest(*args, **kwargs)


def run_optimization(*args, **kwargs) -> OptimizeResult:
    strategy_code = args[0] if args else kwargs.get("strategy_code")
    if not isinstance(strategy_code, str):
        raise TypeError("strategy_code must be a string")
    ensure_strategy_code_allowed(strategy_code)
    return _run_optimization(*args, **kwargs)
