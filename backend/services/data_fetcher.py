"""
data_fetcher.py
yfinance / FinanceDataReader 래퍼 모듈.

- 한국 주식: yfinance 티커 형식 `005930.KS` (코스피), `068760.KQ` (코스닥)
- 미국 주식: `AAPL`, `NVDA` 등 일반 티커
- yfinance 조회 실패 시 FinanceDataReader 로 폴백(가격 데이터 한정)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

import pandas as pd
import yfinance as yf

try:
    import FinanceDataReader as fdr
    _HAS_FDR = True
except Exception:  # pragma: no cover - FDR 미설치 환경 대비
    _HAS_FDR = False

from services import fmp_fetcher


def _use_fmp(ticker: str) -> bool:
    """미국 주식이고 FMP 키가 설정돼 있으면 FMP 를 우선 사용."""
    return not is_korean_ticker(ticker) and fmp_fetcher.enabled()


def _clean(value: Any) -> Any:
    """NaN/inf 등 JSON 직렬화 불가 값을 None 으로 정규화한다."""
    if value is None:
        return None
    if isinstance(value, float):
        if pd.isna(value) or value in (float("inf"), float("-inf")):
            return None
        return round(value, 4)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d")
    return value


def is_korean_ticker(ticker: str) -> bool:
    return ticker.upper().endswith((".KS", ".KQ"))


@lru_cache(maxsize=256)
def _yf_ticker(ticker: str) -> yf.Ticker:
    return yf.Ticker(ticker)


def get_stock_info(ticker: str) -> dict[str, Any]:
    """
    종목 기본 정보 + 핵심 밸류에이션/재무 지표를 반환한다.
    반환 지표: 현재가, 시가총액, PER, PBR, ROE, 배당수익률 등.
    """
    ticker = ticker.strip().upper()

    if _use_fmp(ticker):
        try:
            return fmp_fetcher.get_stock_info(ticker)
        except Exception:
            pass  # FMP 실패 시 yfinance 로 폴백

    t = _yf_ticker(ticker)

    try:
        info = t.info or {}
    except Exception:
        info = {}

    if not info or info.get("regularMarketPrice") is None:
        # 최소한 가격이라도 확보 시도
        price = _last_close(ticker)
        if price is None:
            raise ValueError(f"'{ticker}' 종목 데이터를 찾을 수 없습니다.")
        return {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName") or ticker,
            "market": "KR" if is_korean_ticker(ticker) else "US",
            "currency": "KRW" if is_korean_ticker(ticker) else "USD",
            "price": _clean(price),
            "per": None, "pbr": None, "roe": None,
            "market_cap": None, "dividend_yield": None,
            "sector": None, "industry": None,
        }

    roe = info.get("returnOnEquity")
    dividend = info.get("dividendYield")

    return {
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName") or ticker,
        "market": "KR" if is_korean_ticker(ticker) else "US",
        "currency": info.get("currency") or ("KRW" if is_korean_ticker(ticker) else "USD"),
        "price": _clean(info.get("currentPrice") or info.get("regularMarketPrice")),
        "previous_close": _clean(info.get("previousClose")),
        "market_cap": _clean(info.get("marketCap")),
        "per": _clean(info.get("trailingPE")),
        "forward_per": _clean(info.get("forwardPE")),
        "pbr": _clean(info.get("priceToBook")),
        "roe": _clean(roe * 100 if isinstance(roe, (int, float)) else None),
        "eps": _clean(info.get("trailingEps")),
        # 최신 yfinance는 dividendYield 를 이미 퍼센트 단위로 반환한다(예: 0.37 = 0.37%).
        "dividend_yield": _clean(dividend if isinstance(dividend, (int, float)) else None),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "fifty_two_week_high": _clean(info.get("fiftyTwoWeekHigh")),
        "fifty_two_week_low": _clean(info.get("fiftyTwoWeekLow")),
    }


def get_financials(ticker: str) -> dict[str, Any]:
    """손익계산서/재무상태표/현금흐름표 요약(최근 연도 기준 컬럼별)."""
    ticker = ticker.strip().upper()

    if _use_fmp(ticker):
        try:
            return fmp_fetcher.get_financials(ticker)
        except Exception:
            pass

    t = _yf_ticker(ticker)

    def _frame_to_records(df: pd.DataFrame | None) -> list[dict[str, Any]]:
        if df is None or df.empty:
            return []
        out = []
        for col in df.columns:
            period = _clean(col)
            row = {"period": period}
            for idx, val in df[col].items():
                row[str(idx)] = _clean(val)
            out.append(row)
        return out

    try:
        income = _frame_to_records(t.financials)
    except Exception:
        income = []
    try:
        balance = _frame_to_records(t.balance_sheet)
    except Exception:
        balance = []
    try:
        cashflow = _frame_to_records(t.cashflow)
    except Exception:
        cashflow = []

    return {
        "ticker": ticker,
        "income_statement": income,
        "balance_sheet": balance,
        "cash_flow": cashflow,
    }


def get_price_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> list[dict[str, Any]]:
    """가격 히스토리(차트용). 미국=FMP 우선, 실패 시 yfinance, 그다음 FDR 폴백."""
    ticker = ticker.strip().upper()

    if _use_fmp(ticker):
        try:
            data = fmp_fetcher.get_price_history(ticker, period)
            if data:
                return data
        except Exception:
            pass

    t = _yf_ticker(ticker)

    df: pd.DataFrame | None = None
    try:
        df = t.history(period=period, interval=interval, auto_adjust=False)
    except Exception:
        df = None

    if (df is None or df.empty) and _HAS_FDR:
        df = _fdr_history(ticker, period)

    if df is None or df.empty:
        return []

    records = []
    for date, row in df.iterrows():
        records.append({
            "date": _clean(date),
            "open": _clean(row.get("Open")),
            "high": _clean(row.get("High")),
            "low": _clean(row.get("Low")),
            "close": _clean(row.get("Close")),
            "volume": _clean(row.get("Volume")),
        })
    return records


def _last_close(ticker: str) -> float | None:
    try:
        df = _yf_ticker(ticker).history(period="5d")
        if not df.empty:
            return float(df["Close"].dropna().iloc[-1])
    except Exception:
        pass
    if _HAS_FDR:
        df = _fdr_history(ticker, "5d")
        if df is not None and not df.empty:
            return float(df["Close"].dropna().iloc[-1])
    return None


def _fdr_history(ticker: str, period: str) -> pd.DataFrame | None:
    """FinanceDataReader 폴백. .KS/.KQ 접미사는 코드만 추출해 조회."""
    if not _HAS_FDR:
        return None
    code = ticker.split(".")[0] if is_korean_ticker(ticker) else ticker
    days = _period_to_days(period)
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        df = fdr.DataReader(code, start)
        return df if df is not None and not df.empty else None
    except Exception:
        return None


def _period_to_days(period: str) -> int:
    mapping = {
        "5d": 7, "1mo": 31, "3mo": 93, "6mo": 186,
        "1y": 366, "2y": 731, "5y": 1827, "10y": 3653,
    }
    return mapping.get(period, 366)
