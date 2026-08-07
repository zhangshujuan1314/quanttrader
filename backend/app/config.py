from pydantic import model_validator
from pydantic_settings import BaseSettings


DEFAULT_DEV_JWT_SECRET = "quanttrader-dev-secret-change-in-production"


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./quanttrader.db"
    redis_url: str = "redis://localhost:6379"
    debug: bool = True

    # Default trading config
    default_commission: float = 0.00025  # 0.025%
    default_stamp_duty: float = 0.0005   # 0.05% (sell only)
    default_slippage: float = 0.001      # 0.1%
    default_initial_cash: float = 100000.0

    # Risk limits
    max_daily_loss_pct: float = -0.05
    max_position_pct: float = 0.80
    single_stock_limit_pct: float = 0.20
    single_stop_loss_pct: float = -0.08

    # Auth
    jwt_secret: str = DEFAULT_DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # Strategy execution
    # Custom Python strategies are arbitrary code. Keep remote execution disabled
    # unless an operator explicitly accepts that risk in a trusted environment.
    allow_unsafe_strategy_exec: bool = False

    model_config = {"env_prefix": "QT_", "env_file": ".env"}

    @model_validator(mode="after")
    def validate_production_security(self):
        """Fail closed when production-like mode uses a known/weak JWT secret."""
        if not self.debug:
            if self.jwt_secret == DEFAULT_DEV_JWT_SECRET or len(self.jwt_secret) < 32:
                raise ValueError(
                    "QT_JWT_SECRET must be set to a strong value of at least 32 characters when QT_DEBUG=false"
                )
        return self


settings = Settings()
