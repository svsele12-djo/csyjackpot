"""
screen.py — 퀀트 스크리닝 라우터.
POST /api/screen
    { "tickers": ["AAPL","005930.KS",...],
      "filters": { "per_max": 20, "pbr_max": 2, "roe_min": 10,
                   "dividend_min": 1, "market_cap_min": 0 } }
→ 사용자가 입력한 티커들을 조건으로 필터링해 통과/탈락 결과를 반환.
"""
from pydantic import BaseModel, Field
from fastapi import APIRouter

from services import data_fetcher

router = APIRouter(prefix="/api", tags=["screen"])


class ScreenFilters(BaseModel):
    per_max: float | None = None          # PER 이하
    pbr_max: float | None = None          # PBR 이하
    roe_min: float | None = None          # ROE(%) 이상
    dividend_min: float | None = None     # 배당수익률(%) 이상
    market_cap_min: float | None = None   # 시가총액 이상(현지통화)


class ScreenRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=1)
    filters: ScreenFilters = ScreenFilters()


def _check(info: dict, f: ScreenFilters) -> tuple[bool, list[str]]:
    """조건 통과 여부와 탈락 사유 목록을 반환한다. 값이 없으면 해당 조건은 통과 처리(불이익 없음)."""
    reasons: list[str] = []

    def fail(cond: bool, msg: str):
        if cond:
            reasons.append(msg)

    if f.per_max is not None and info.get("per") is not None:
        fail(info["per"] > f.per_max, f"PER {info['per']} > {f.per_max}")
    if f.pbr_max is not None and info.get("pbr") is not None:
        fail(info["pbr"] > f.pbr_max, f"PBR {info['pbr']} > {f.pbr_max}")
    if f.roe_min is not None and info.get("roe") is not None:
        fail(info["roe"] < f.roe_min, f"ROE {info['roe']} < {f.roe_min}")
    if f.dividend_min is not None and info.get("dividend_yield") is not None:
        fail(info["dividend_yield"] < f.dividend_min, f"배당 {info['dividend_yield']} < {f.dividend_min}")
    if f.market_cap_min is not None and info.get("market_cap") is not None:
        fail(info["market_cap"] < f.market_cap_min, f"시총 < {f.market_cap_min}")

    return (len(reasons) == 0, reasons)


@router.post("/screen")
def screen(req: ScreenRequest):
    results = []
    passed = 0
    # 중복 제거 + 정규화
    seen = set()
    for raw in req.tickers:
        ticker = raw.strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)

        try:
            info = data_fetcher.get_stock_info(ticker)
        except Exception as e:
            results.append({
                "ticker": ticker, "ok": False, "error": str(e),
                "passed": False, "reasons": ["조회 실패"],
            })
            continue

        ok, reasons = _check(info, req.filters)
        if ok:
            passed += 1
        results.append({
            "ticker": ticker,
            "ok": True,
            "passed": ok,
            "reasons": reasons,
            "name": info.get("name"),
            "currency": info.get("currency"),
            "price": info.get("price"),
            "per": info.get("per"),
            "pbr": info.get("pbr"),
            "roe": info.get("roe"),
            "dividend_yield": info.get("dividend_yield"),
            "market_cap": info.get("market_cap"),
        })

    # 통과 종목을 위로 정렬
    results.sort(key=lambda r: (not r["passed"], r["ticker"]))
    return {
        "total": len(results),
        "passed": passed,
        "filters": req.filters.model_dump(),
        "results": results,
    }
