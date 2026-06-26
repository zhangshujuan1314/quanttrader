from pydantic_settings import BaseSettings


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
    jwt_secret: str = "quanttrader-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    model_config = {"env_prefix": "QT_", "env_file": ".env"}


settings = Settings()
