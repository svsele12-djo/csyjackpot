"""
backtest.py — 백테스트 라우터.
POST /api/backtest
    { "tickers": ["AAPL","MSFT"], "period": "3y",
      "rebalance": "quarterly", "initial_capital": 10000000, "cost_rate": 0.003 }
→ 동일비중 포트폴리오의 수익률 곡선 + 성과지표.
"""
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from services import backtest_engine

router = APIRouter(prefix="/api", tags=["backtest"])


class BacktestRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=1)
    period: str = "3y"                      # 1y,2y,3y,5y,10y
    rebalance: str = "quarterly"            # none,monthly,quarterly,yearly
    initial_capital: float = 10_000_000
    cost_rate: float = 0.003                # 0.3%


@router.post("/backtest")
def backtest(req: BacktestRequest):
    try:
        return backtest_engine.run_backtest(
            tickers=req.tickers,
            period=req.period,
            rebalance=req.rebalance,
            initial_capital=req.initial_capital,
            cost_rate=req.cost_rate,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"백테스트 실패: {e}")
