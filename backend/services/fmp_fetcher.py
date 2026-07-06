"""
fmp_fetcher.py — Financial Modeling Prep(/stable) 래퍼.

미국 주식 데이터를 FMP 로 조회한다. 무료 티어는 250콜/일·미국만이므로
15분 TTL 메모리 캐시로 호출 수를 절약한다.
키가 없으면 enabled()=False → 호출측에서 yfinance 로 폴백한다.

- get_stock_info: profile + ratios-ttm + key-metrics-ttm (3콜)
- get_financials:  income-statement (1콜, 6시간 캐시)
- get_price_history: historical-price-eod/light (1콜, 3시간 캐시)
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any

from dotenv import load_dotenv

load_dotenv()  # backend/.env 로드 (uvicorn 이 backend/ 에서 실행됨)

_API_KEY = os.getenv("FMP_API_KEY", "").strip()
_BASE = "https://financialmodelingprep.com/stable"
_cache: dict[str, tuple[float, Any]] = {}


def enabled() -> bool:
    return bool(_API_KEY) and "붙여넣" not in _API_KEY


def _get(path: str, ttl: int = 900) -> Any:
    now = time.time()
    hit = _cache.get(path)
    if hit and hit[0] > now:
        return hit[1]
    sep = "&" if "?" in path else "?"
    url = f"{_BASE}/{path}{sep}apikey={_API_KEY}"
    req = urllib.request.Request(url, headers={"User-Agent": "pioneer/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode())
    # FMP 는 에러도 200 + {"Error Message": ...} 로 줄 수 있음
    if isinstance(data, dict) and "Error Message" in data:
        raise RuntimeError(data["Error Message"])
    _cache[path] = (now + ttl, data)
    return data


def _one(data: Any) -> dict:
    if isinstance(data, list) and data:
        return data[0]
    return data if isinstance(data, dict) else {}


def _f(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


def get_stock_info(ticker: str) -> dict[str, Any]:
    t = ticker.strip().upper()
    profile = _one(_get(f"profile?symbol={t}"))
    if not profile or profile.get("price") is None:
        raise ValueError(f"'{t}' FMP 데이터 없음")

    ratios = _one(_get(f"ratios-ttm?symbol={t}"))
    metrics = _one(_get(f"key-metrics-ttm?symbol={t}"))

    price = _f(profile.get("price"))
    change = _f(profile.get("change"))
    prev = round(price - change, 4) if price is not None and change is not None else None

    low = high = None
    rng = str(profile.get("range") or "")
    if "-" in rng:
        parts = rng.split("-")
        if len(parts) == 2:
            low, high = _f(parts[0]), _f(parts[1])

    roe = metrics.get("returnOnEquityTTM")
    div = ratios.get("dividendYieldTTM")

    return {
        "ticker": t,
        "name": profile.get("companyName") or t,
        "market": "US",
        "currency": profile.get("currency") or "USD",
        "price": price,
        "previous_close": prev,
        "market_cap": _f(profile.get("marketCap")),
        "per": _f(ratios.get("priceToEarningsRatioTTM")),
        "forward_per": None,  # FMP 무료 티어에 선행 PER 미제공
        "pbr": _f(ratios.get("priceToBookRatioTTM")),
        "roe": round(roe * 100, 4) if isinstance(roe, (int, float)) else None,
        "eps": _f(ratios.get("netIncomePerShareTTM")),
        "dividend_yield": round(div * 100, 4) if isinstance(div, (int, float)) else None,
        "sector": profile.get("sector"),
        "industry": profile.get("industry"),
        "fifty_two_week_high": high,
        "fifty_two_week_low": low,
    }


def get_financials(ticker: str) -> dict[str, Any]:
    t = ticker.strip().upper()
    data = _get(f"income-statement?symbol={t}&period=annual&limit=5", ttl=21600)
    records = []
    for r in data if isinstance(data, list) else []:
        records.append({
            "period": str(r.get("fiscalYear") or str(r.get("date") or "")[:4]),
            "Total Revenue": _f(r.get("revenue")),
            "Gross Profit": _f(r.get("grossProfit")),
            "Operating Income": _f(r.get("operatingIncome")),
            "Net Income": _f(r.get("netIncome")),
        })
    return {
        "ticker": t,
        "income_statement": records,
        "balance_sheet": [],
        "cash_flow": [],
    }


# period → 가져올 거래일(행) 개수 (light 는 최신순 전체를 주므로 앞에서 잘라 사용)
_PERIOD_ROWS = {
    "5d": 5, "1mo": 22, "3mo": 66, "6mo": 126,
    "1y": 252, "2y": 504, "5y": 1260, "10y": 2520,
}


def get_price_history(ticker: str, period: str = "1y") -> list[dict[str, Any]]:
    t = ticker.strip().upper()
    data = _get(f"historical-price-eod/light?symbol={t}", ttl=10800)
    if not isinstance(data, list) or not data:
        return []
    rows = data[: _PERIOD_ROWS.get(period, 252)]
    records = []
    for row in reversed(rows):  # 최신순 → 오래된순(차트용)
        close = _f(row.get("price"))
        records.append({
            "date": row.get("date"),
            "open": close, "high": close, "low": close,
            "close": close,
            "volume": _f(row.get("volume")),
        })
    return records
