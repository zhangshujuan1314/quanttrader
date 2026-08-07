import pytest
from pydantic import ValidationError

from app.config import DEFAULT_DEV_JWT_SECRET, Settings


def test_debug_mode_allows_local_default_secret():
    settings = Settings(_env_file=None, debug=True, jwt_secret=DEFAULT_DEV_JWT_SECRET)
    assert settings.debug is True


def test_non_debug_mode_rejects_repository_default_secret():
    with pytest.raises(ValidationError, match="QT_JWT_SECRET"):
        Settings(_env_file=None, debug=False, jwt_secret=DEFAULT_DEV_JWT_SECRET)


def test_non_debug_mode_rejects_short_secret():
    with pytest.raises(ValidationError, match="QT_JWT_SECRET"):
        Settings(_env_file=None, debug=False, jwt_secret="too-short")


def test_non_debug_mode_accepts_strong_secret():
    settings = Settings(_env_file=None, debug=False, jwt_secret="a" * 32)
    assert settings.jwt_secret == "a" * 32
