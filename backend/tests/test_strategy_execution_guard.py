import pytest

from app.config import settings
from app.domain.strategy.engine import STRATEGY_TEMPLATES
from app.domain.strategy.safe_engine import ensure_strategy_code_allowed, is_builtin_strategy_code


def test_builtin_strategy_templates_are_allowed():
    for template in STRATEGY_TEMPLATES.values():
        assert is_builtin_strategy_code(template["code"])
        ensure_strategy_code_allowed(template["code"])


def test_custom_strategy_is_denied_by_default():
    original = settings.allow_unsafe_strategy_exec
    settings.allow_unsafe_strategy_exec = False
    try:
        with pytest.raises(PermissionError, match="Custom Python strategy execution is disabled"):
            ensure_strategy_code_allowed("import os\nclass Evil: pass")
    finally:
        settings.allow_unsafe_strategy_exec = original


def test_operator_can_explicitly_opt_into_trusted_custom_code():
    original = settings.allow_unsafe_strategy_exec
    settings.allow_unsafe_strategy_exec = True
    try:
        ensure_strategy_code_allowed("class TrustedLocalStrategy: pass")
    finally:
        settings.allow_unsafe_strategy_exec = original
