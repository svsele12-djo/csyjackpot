"""
main.py — 파이어니어(Pioneer) 퀀트 투자 웹서비스 FastAPI 진입점.

로컬 실행:
    cd backend
    uvicorn main:app --reload --port 8000
그러면 http://127.0.0.1:8000 에서 프론트엔드까지 함께 서빙된다.
API 문서는 http://127.0.0.1:8000/docs

배포(Render 등): 이 한 서비스가 API(/api/*)와 프론트엔드(정적)를 모두 제공한다.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import stock, screen, backtest, portfolio

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="Pioneer Quant API",
    description="퀀트 투자 웹서비스 - 종목 조회 / 스크리닝 / 백테스트 / 포트폴리오",
    version="0.1.0",
)

# 통합 배포(같은 오리진)에서는 CORS 가 불필요하지만, 프론트를 별도 배포하는
# 경우(GitHub Pages 등)를 대비해 허용해 둔다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API 라우터 (정적 마운트보다 먼저 등록해야 /api/* 가 우선 매칭됨) ---
app.include_router(stock.router)
app.include_router(screen.router)
app.include_router(backtest.router)
app.include_router(portfolio.router)


@app.get("/api/health")
def health():
    return {"status": "healthy"}


# --- 프론트엔드 정적 파일 서빙 (반드시 마지막에 마운트) ---
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
