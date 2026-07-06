"""
stock.py — 종목 조회 라우터.
GET /api/stock/{ticker}          → 기본정보 + 밸류에이션 지표
GET /api/stock/{ticker}/financials → 재무제표 요약
GET /api/stock/{ticker}/history    → 가격 히스토리(차트용)
"""
from fastapi import APIRouter, HTTPException, Query

from services import data_fetcher, stock_search

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/search")
def search_stock(
    q: str = Query(..., min_length=1, description="종목명(한글/영문) 또는 코드"),
    limit: int = Query(15, ge=1, le=50),
):
    try:
        return {"query": q, "results": stock_search.search(q, limit)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"검색 실패: {e}")


@router.get("/{ticker}")
def read_stock(ticker: str):
    try:
        return data_fetcher.get_stock_info(ticker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"데이터 조회 실패: {e}")


@router.get("/{ticker}/financials")
def read_financials(ticker: str):
    try:
        return data_fetcher.get_financials(ticker)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"재무 데이터 조회 실패: {e}")


@router.get("/{ticker}/history")
def read_history(
    ticker: str,
    period: str = Query("1y", description="5d,1mo,3mo,6mo,1y,2y,5y"),
    interval: str = Query("1d", description="1d,1wk,1mo"),
):
    try:
        data = data_fetcher.get_price_history(ticker, period, interval)
        return {"ticker": ticker.upper(), "period": period, "prices": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"가격 조회 실패: {e}")
