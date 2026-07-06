"""
portfolio.py — 포트폴리오 평가 라우터.
POST /api/portfolio
    { "holdings": [ {"ticker":"AAPL","shares":10,"avg_price":180},
                    {"ticker":"005930.KS","shares":50,"avg_price":70000} ] }
→ 보유종목별 현재가/평가액/손익/비중 + 합계.

보유내역(holdings)은 프론트엔드가 localStorage 로 관리하고,
평가 시점에만 서버로 보내 현재가·수익률을 계산한다.
통화가 다른 종목이 섞이면 비중은 각 통화 그대로 합산하므로
동일 통화로 구성할 때 의미가 정확하다(데모 단순화).
"""
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from services import data_fetcher

router = APIRouter(prefix="/api", tags=["portfolio"])


class Holding(BaseModel):
    ticker: str
    shares: float = Field(..., gt=0)
    avg_price: float = Field(..., ge=0)


class PortfolioRequest(BaseModel):
    holdings: list[Holding] = Field(..., min_length=1)


@router.post("/portfolio")
def evaluate(req: PortfolioRequest):
    rows = []
    total_value = 0.0
    total_cost = 0.0

    for h in req.holdings:
        ticker = h.ticker.strip().upper()
        try:
            info = data_fetcher.get_stock_info(ticker)
            price = info.get("price")
            name = info.get("name")
            currency = info.get("currency")
        except Exception as e:
            rows.append({
                "ticker": ticker, "ok": False, "error": str(e),
                "shares": h.shares, "avg_price": h.avg_price,
            })
            continue

        if price is None:
            rows.append({
                "ticker": ticker, "ok": False, "error": "현재가 없음",
                "shares": h.shares, "avg_price": h.avg_price,
            })
            continue

        market_value = price * h.shares
        cost = h.avg_price * h.shares
        pnl = market_value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else None

        total_value += market_value
        total_cost += cost

        rows.append({
            "ticker": ticker,
            "ok": True,
            "name": name,
            "currency": currency,
            "shares": h.shares,
            "avg_price": h.avg_price,
            "price": price,
            "market_value": round(market_value, 2),
            "cost": round(cost, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
        })

    # 비중 계산(평가 가능한 종목 기준)
    for r in rows:
        if r.get("ok") and total_value > 0:
            r["weight"] = round(r["market_value"] / total_value * 100, 2)

    total_pnl = total_value - total_cost
    return {
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / total_cost * 100, 2) if total_cost > 0 else None,
        "holdings": rows,
    }
