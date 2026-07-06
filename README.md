# csyjackpot — 퀀트 투자 웹서비스

mzbfire.com 유사 정량 데이터 분석/퀀트 투자 웹서비스. FastAPI 백엔드 + 정적 프론트엔드.

## 기능
1. **종목 조회** — 한글/영문 종목명 자동완성 검색 + 기본정보 + 밸류에이션 지표(PER/PBR/ROE/배당) + 가격차트 + 재무제표
2. **퀀트 스크리닝** — 입력한 티커 목록을 조건(PER/PBR/ROE/배당)으로 필터링
3. **백테스트** — 동일비중 포트폴리오, 주기별 리밸런싱, 거래비용 반영, 자산곡선 + 성과지표(CAGR/MDD/변동성/샤프)
4. **포트폴리오** — 보유종목 현재가/평가손익/비중 (보유내역은 브라우저 localStorage 저장)

## 기술 스택
- 백엔드: Python FastAPI + yfinance + FinanceDataReader
- 프론트엔드: 정적 HTML/JS + Chart.js (CDN)

## 로컬 실행 (Windows)

### 1) 백엔드
```powershell
cd backend
py -3 -m venv .venv                       # 최초 1회
.\.venv\Scripts\python.exe -m pip install -r requirements.txt   # 최초 1회
copy .env.example .env                     # 최초 1회, 이후 .env 에 FMP 키 입력
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```
API 문서: http://127.0.0.1:8000/docs

#### 미국 주식 데이터 소스 (FMP)
- 미국 주식은 **Financial Modeling Prep(FMP)** `/stable` API 를 우선 사용한다. `backend/.env` 의 `FMP_API_KEY` 에 키를 넣으면 활성화된다(무료 티어: **250콜/일·미국만**).
- 키가 없거나 FMP 호출이 실패하면 **자동으로 yfinance 로 폴백**한다.
- 한국 주식은 FMP 무료 티어 미지원 → 계속 FinanceDataReader/yfinance 사용.
- 호출 절약을 위해 종목정보는 15분, 재무 6시간, 가격 3시간 **메모리 캐시**를 둔다. 종목 1개 완전 조회 ≈ 5콜(정보 3 + 재무 1 + 차트 1).
- ⚠️ `.env` 는 절대 커밋 금지(`.gitignore` 등록됨). 배포 시 Render 등의 **환경변수**로 `FMP_API_KEY` 를 설정한다.

### 2) 프론트엔드 (정적 서버)
```powershell
cd frontend
py -3 -m http.server 5500
```
브라우저에서 http://127.0.0.1:5500 접속.

> 프론트엔드는 `localhost`/`127.0.0.1` 로 접속하면 자동으로 `http://127.0.0.1:8000` 백엔드를 호출한다.
> `file://` 로 직접 열면 CORS 로 인해 API 호출이 실패하므로 반드시 http 서버로 서빙할 것.

## API 엔드포인트
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET  | `/api/stock/search?q=한화` | 종목명(한글/영문)·코드로 검색(자동완성) |
| GET  | `/api/stock/{ticker}` | 종목 기본정보 + 지표 |
| GET  | `/api/stock/{ticker}/financials` | 재무제표 요약 |
| GET  | `/api/stock/{ticker}/history?period=1y` | 가격 히스토리 |
| POST | `/api/screen` | 퀀트 스크리닝 |
| POST | `/api/backtest` | 백테스트 |
| POST | `/api/portfolio` | 포트폴리오 평가 |

## 티커 형식
- 한국: `005930.KS`(삼성전자, 코스피), `068760.KQ`(코스닥)
- 미국: `AAPL`, `NVDA` 등

## 배포 (GitHub + Render 통합)

FastAPI 한 서비스가 API(`/api/*`)와 프론트엔드(정적)를 **함께 서빙**한다. URL 하나 · CORS 불필요 · 배포 한 번.

### 1) GitHub 에 올리기
```powershell
# (최초 1회) 저장소는 github.com 에서 먼저 새로 만든다: 예) csyjackpot  (README/.gitignore 추가 안 함)
git remote add origin https://github.com/<사용자명>/<저장소명>.git
git push -u origin main
```
이미 `git init` + 최초 커밋은 되어 있음. `.env`(FMP 키)는 `.gitignore` 로 제외되어 올라가지 않는다.

### 2) Render 에 배포 (Blueprint)
1. https://render.com 가입 → GitHub 연동
2. **New + → Blueprint** → 이 저장소 선택 → `render.yaml` 자동 인식
3. 배포 중 **환경변수 `FMP_API_KEY`** 에 FMP 키 입력 (blueprint 에는 값이 없음)
4. 배포 완료 후 `https://csyjackpot-xxxx.onrender.com` 접속 → 프론트+API 모두 동작

> - 무료 플랜은 15분 미사용 시 슬립 → 첫 요청 30초~1분 지연.
> - 코드 push 시 Render 가 자동 재배포.
> - 프론트를 GitHub Pages 등 **다른 도메인**에 따로 올릴 경우에만, 페이지에서 `window.CSYJACKPOT_API_BASE = "https://<render주소>"` 로 백엔드 주소를 지정한다.

## 알려진 단순화(데모)
- 스크리닝: 지표값이 없으면(null) 해당 조건은 무시하고 통과 처리 (없는 데이터로 불이익 없음).
- 백테스트/포트폴리오: 통화가 다른 종목을 섞으면 환율을 무시하고 합성/합산한다. 정확한 결과는 동일 통화로 구성할 것.
- 백테스트 거래비용은 리밸런싱 회전율에 비례해 차감(기본 0.3%).
