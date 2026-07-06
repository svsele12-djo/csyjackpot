// portfolio.js — 포트폴리오 페이지 로직 (보유내역 localStorage 관리 + 서버 평가)

const STORE_KEY = "pioneer_holdings";

function loadHoldings() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
  } catch (_) {
    return [];
  }
}
function saveHoldings(h) {
  localStorage.setItem(STORE_KEY, JSON.stringify(h));
}

function fmt(v, d = 2) {
  if (v === null || v === undefined) return "—";
  return Number(v).toLocaleString("ko-KR", { maximumFractionDigits: d });
}
function signCls(v) {
  if (v === null || v === undefined) return "";
  return v >= 0 ? "r-pass" : "reject";
}
function setStatus(msg, isError = false) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = "status" + (isError ? " error" : "");
  el.classList.remove("hidden");
}

// 입력된 보유내역 목록 렌더링(삭제 버튼 포함)
function renderHoldings() {
  const holdings = loadHoldings();
  const wrap = document.getElementById("holdingsList");
  if (!holdings.length) {
    wrap.innerHTML = '<div class="hint">아직 보유종목이 없습니다. 위에서 추가하세요.</div>';
    return;
  }
  let html = `<table class="fin"><thead><tr>
    <th>티커</th><th>수량</th><th>평균단가</th><th></th></tr></thead><tbody>`;
  holdings.forEach((h, i) => {
    html += `<tr>
      <td style="text-align:left">${h.ticker}</td>
      <td>${fmt(h.shares)}</td>
      <td>${fmt(h.avg_price)}</td>
      <td><button data-idx="${i}" class="delBtn" style="background:none;border:none;color:var(--up);cursor:pointer;font-size:13px;">삭제</button></td>
    </tr>`;
  });
  html += "</tbody></table>";
  wrap.innerHTML = html;
  wrap.querySelectorAll(".delBtn").forEach((btn) =>
    btn.addEventListener("click", () => {
      const idx = Number(btn.dataset.idx);
      const list = loadHoldings();
      list.splice(idx, 1);
      saveHoldings(list);
      renderHoldings();
    })
  );
}

function addHolding() {
  const ticker = document.getElementById("pTicker").value.trim().toUpperCase();
  const shares = Number(document.getElementById("pShares").value);
  const avg = Number(document.getElementById("pAvg").value);
  if (!ticker || !(shares > 0) || !(avg >= 0)) {
    setStatus("티커/수량/평균단가를 올바르게 입력하세요.", true);
    return;
  }
  const list = loadHoldings();
  list.push({ ticker, shares, avg_price: avg });
  saveHoldings(list);
  document.getElementById("pTicker").value = "";
  document.getElementById("pShares").value = "";
  document.getElementById("pAvg").value = "";
  document.getElementById("status").classList.add("hidden");
  renderHoldings();
}

function renderResult(data) {
  document.getElementById("status").classList.add("hidden");

  const summary = [
    ["총 평가액", fmt(data.total_value, 0), null],
    ["총 매입액", fmt(data.total_cost, 0), null],
    ["평가손익", fmt(data.total_pnl, 0), data.total_pnl],
    ["수익률", data.total_pnl_pct != null ? fmt(data.total_pnl_pct) + "%" : "—", data.total_pnl_pct],
  ];
  const sEl = document.getElementById("summary");
  sEl.innerHTML = "";
  summary.forEach(([k, v, color]) => {
    const cls = "v" + (typeof color === "number" ? " " + signCls(color) : "");
    const d = document.createElement("div");
    d.className = "metric";
    d.innerHTML = `<div class="k">${k}</div><div class="${cls}">${v}</div>`;
    sEl.appendChild(d);
  });

  let html = `<table class="fin"><thead><tr>
    <th>티커</th><th>종목명</th><th>수량</th><th>평균단가</th><th>현재가</th>
    <th>평가액</th><th>손익</th><th>수익률</th><th>비중</th></tr></thead><tbody>`;
  data.holdings.forEach((r) => {
    if (!r.ok) {
      html += `<tr><td style="text-align:left">${r.ticker}</td>
        <td colspan="8" class="reject">${r.error || "평가 실패"}</td></tr>`;
      return;
    }
    html += `<tr>
      <td style="text-align:left">${r.ticker}</td>
      <td style="text-align:left">${r.name || "—"}</td>
      <td>${fmt(r.shares)}</td>
      <td>${fmt(r.avg_price)}</td>
      <td>${fmt(r.price)}</td>
      <td>${fmt(r.market_value, 0)}</td>
      <td class="${signCls(r.pnl)}">${fmt(r.pnl, 0)}</td>
      <td class="${signCls(r.pnl_pct)}">${r.pnl_pct != null ? fmt(r.pnl_pct) + "%" : "—"}</td>
      <td>${r.weight != null ? fmt(r.weight) + "%" : "—"}</td>
    </tr>`;
  });
  html += "</tbody></table>";
  document.getElementById("table").innerHTML = html;
  document.getElementById("result").classList.remove("hidden");
}

async function evaluate() {
  const holdings = loadHoldings();
  if (!holdings.length) {
    setStatus("보유종목을 먼저 추가하세요.", true);
    return;
  }
  document.getElementById("result").classList.add("hidden");
  setStatus("현재가 평가 중...");
  try {
    const data = await PioneerAPI.portfolio(holdings);
    renderResult(data);
  } catch (e) {
    setStatus(`평가 실패: ${e.message}`, true);
  }
}

document.getElementById("addBtn").addEventListener("click", addHolding);
document.getElementById("evalBtn").addEventListener("click", evaluate);
document.getElementById("pAvg").addEventListener("keydown", (e) => {
  if (e.key === "Enter") addHolding();
});
renderHoldings();
