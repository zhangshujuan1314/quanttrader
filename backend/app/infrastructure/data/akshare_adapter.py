"""akshare data adapter — free A-share market data."""
from datetime import date, timedelta
import pandas as pd
import akshare as ak
from app.infrastructure.data.base import DataAdapter


class AkshareAdapter(DataAdapter):
    """ponytail: one adapter for MVP. tushare/joinquant later."""

    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        # akshare uses raw code (no exchange prefix for stock_zh_a_hist)
        raw = symbol.split(".")[0] if "." in symbol else symbol
        df = ak.stock_zh_a_hist(symbol=raw, period="daily",
                                start_date=start.strftime("%Y%m%d"),
                                end_date=end.strftime("%Y%m%d"),
                                adjust="qfq")  # 前复权
        if df.empty:
            return pd.DataFrame()

        df = df.rename(columns={
            "日期": "trade_date", "开盘": "open", "最高": "high",
            "最低": "low", "收盘": "close", "成交量": "volume",
            "成交额": "amount", "股票代码": "ts_code",
        })
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
        df["ts_code"] = symbol
        # ponytail: adj_factor=1 for qfq, fine for MVP
        df["adj_factor"] = 1.0
        # akshare already has qfq adjusted prices in close column
        return df[["ts_code", "trade_date", "open", "high", "low",
                    "close", "volume", "amount", "adj_factor"]]

    def fetch_stock_list(self) -> pd.DataFrame:
        df = ak.stock_info_a_code_name()
        return df.rename(columns={"code": "ts_code", "name": "name"})

    def is_trading_day(self, d: date) -> bool:
        # ponytail: rough check — weekend is never trading day
        if d.weekday() >= 5:
            return False
        return True
