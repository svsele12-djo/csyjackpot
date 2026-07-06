// api.js — 백엔드 API 호출 래퍼
// 기본은 "같은 오리진"(FastAPI 가 프론트까지 서빙하는 통합 배포/로컬 8000).
// 정적 개발서버(py -m http.server 5500)로 프론트만 따로 띄운 경우에만 8000 백엔드로 보낸다.
// 프론트를 완전히 별도 도메인에 배포하면 window.CSYJACKPOT_API_BASE 로 백엔드 주소를 지정한다.
const API_BASE =
  window.CSYJACKPOT_API_BASE ??
  (location.port === "5500" ? "http://127.0.0.1:8000" : "");

async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

async function apiPost(path, payload) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

const CsyjackpotAPI = {
  getStock: (ticker) => apiGet(`/api/stock/${encodeURIComponent(ticker)}`),
  searchStock: (q, limit = 15) =>
    apiGet(`/api/stock/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  getFinancials: (ticker) =>
    apiGet(`/api/stock/${encodeURIComponent(ticker)}/financials`),
  getHistory: (ticker, period = "1y") =>
    apiGet(`/api/stock/${encodeURIComponent(ticker)}/history?period=${period}`),
  screen: (tickers, filters) => apiPost(`/api/screen`, { tickers, filters }),
  backtest: (payload) => apiPost(`/api/backtest`, payload),
  portfolio: (holdings) => apiPost(`/api/portfolio`, { holdings }),
};
