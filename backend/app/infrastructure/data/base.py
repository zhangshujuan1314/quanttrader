from abc import ABC, abstractmethod
from datetime import date
import pandas as pd


class DataAdapter(ABC):
    @abstractmethod
    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        ...

    @abstractmethod
    def fetch_stock_list(self) -> pd.DataFrame:
        ...

    @abstractmethod
    def is_trading_day(self, d: date) -> bool:
        ...
