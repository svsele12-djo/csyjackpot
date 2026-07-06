"""
stock_search.py — 종목명/코드로 종목을 검색해 후보 목록을 반환.

- 한글 또는 6자리 숫자 코드 → KRX(코스피/코스닥/코넥스) 목록에서 검색
- 영문/심볼 → 미국(NASDAQ+NYSE) 목록에서 심볼/회사명 검색 + KRX 영문명도 보조 검색
- 목록은 최초 1회 로드 후 메모리 캐시 (미국 목록은 지연 로드, 첫 호출 시 수 초 소요)

반환: [{ "ticker": "000880.KS", "name": "한화", "market": "KR", "exchange": "KOSPI" }, ...]
"""
from __future__ import annotations

import re
from typing import Any

try:
    import FinanceDataReader as fdr
    _HAS_FDR = True
except Exception:  # pragma: no cover
    _HAS_FDR = False

_krx_cache = None   # pandas.DataFrame(Code, Name, Market)
_us_cache = None    # pandas.DataFrame(Symbol, Name)

_KR_SUFFIX = {"KOSPI": ".KS"}  # 그 외(KOSDAQ/KOSDAQ GLOBAL/KONEX)는 .KQ


def _has_korean(s: str) -> bool:
    return bool(re.search(r"[가-힣]", s))


def _krx_ticker(code: str, market: str) -> str:
    suffix = _KR_SUFFIX.get(market, ".KQ")
    return f"{code}{suffix}"


def _load_krx():
    global _krx_cache
    if _krx_cache is None and _HAS_FDR:
        df = fdr.StockListing("KRX")
        df = df[["Code", "Name", "Market"]].dropna(subset=["Code", "Name"]).copy()
        df["Name"] = df["Name"].astype(str)
        df["Code"] = df["Code"].astype(str)
        _krx_cache = df
    return _krx_cache


def _load_us():
    global _us_cache
    if _us_cache is None and _HAS_FDR:
        frames = []
        for market in ("NASDAQ", "NYSE"):
            try:
                d = fdr.StockListing(market)[["Symbol", "Name"]].copy()
                frames.append(d)
            except Exception:
                pass
        if frames:
            import pandas as pd
            df = pd.concat(frames, ignore_index=True).dropna(subset=["Symbol"])
            df["Symbol"] = df["Symbol"].astype(str)
            df["Name"] = df["Name"].astype(str)
            _us_cache = df.drop_duplicates(subset=["Symbol"])
    return _us_cache


def _rank(name: str, q: str) -> int:
    """정렬 우선순위: 완전일치(0) < 접두일치(1) < 부분일치(2)."""
    n = name.lower()
    ql = q.lower()
    if n == ql:
        return 0
    if n.startswith(ql):
        return 1
    return 2


def _search_krx(q: str, limit: int) -> list[dict[str, Any]]:
    df = _load_krx()
    if df is None:
        return []
    if q.isdigit():
        mask = df["Code"].str.contains(q, na=False)
    else:
        mask = df["Name"].str.contains(re.escape(q), case=False, na=False)
    hits = df[mask].copy()
    if hits.empty:
        return []
    # 코넥스는 뒤로
    hits["_konex"] = hits["Market"].str.contains("KONEX", na=False).astype(int)
    hits["_rank"] = hits["Name"].apply(lambda n: _rank(n, q))
    hits = hits.sort_values(["_rank", "_konex", "Name"]).head(limit)
    return [
        {
            "ticker": _krx_ticker(r.Code, r.Market),
            "name": r.Name,
            "market": "KR",
            "exchange": r.Market,
        }
        for r in hits.itertuples()
    ]


def _search_us(q: str, limit: int) -> list[dict[str, Any]]:
    df = _load_us()
    if df is None:
        return []
    ql = q.lower()
    mask = df["Symbol"].str.lower().str.contains(re.escape(ql), na=False) | df[
        "Name"
    ].str.lower().str.contains(re.escape(ql), na=False)
    hits = df[mask].copy()
    if hits.empty:
        return []
    # 심볼 완전일치 최우선
    hits["_rank"] = hits.apply(
        lambda r: 0 if r.Symbol.lower() == ql else _rank(r.Name, q), axis=1
    )
    hits = hits.sort_values(["_rank", "Symbol"]).head(limit)
    return [
        {"ticker": r.Symbol, "name": r.Name, "market": "US", "exchange": "US"}
        for r in hits.itertuples()
    ]


def search(q: str, limit: int = 15) -> list[dict[str, Any]]:
    q = (q or "").strip()
    if not q:
        return []

    if _has_korean(q) or q.isdigit():
        return _search_krx(q, limit)

    # 영문/심볼: 미국 우선, 부족하면 KRX 영문명 보조
    results = _search_us(q, limit)
    if len(results) < limit:
        results += _search_krx(q, limit - len(results))
    return results[:limit]
