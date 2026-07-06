// backtest.js — 백테스트 페이지 로직

function fmtWon(v) {
  if (v === null || v === undefined) return "—";
  return "₩" + Number(v).toLocaleString("ko-KR", { maximumFractionDigits: 0 });
}
function pct(v) {
  if (v === null || v === undefined) return "—";
  const s = v >= 0 ? "+" : "";
  return s + Number(v).toLocaleString("ko-KR", { maximumFractionDigits: 2 }) + "%";
}

function setStatus(msg, isError = false) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = "status" + (isError ? " error" : "");
  el.classList.remove("hidden");
}

function renderMetrics(data) {
  const m = data.metrics;
  document.getElementById("rangeTitle").textContent =
    `${data.tickers.join(", ")} · ${data.start} ~ ${data.end} · 리밸런싱 ${data.rebalance}`;

  const items = [
    ["최종 평가액", fmtWon(m.final_value), null],
    ["누적 수익률", pct(m.total_return_pct), m.total_return_pct],
    ["연평균(CAGR)", pct(m.cagr_pct), m.cagr_pct],
    ["최대낙폭(MDD)", pct(m.mdd_pct), m.mdd_pct],
    ["변동성(연)", (m.volatility_pct ?? "—") + "%", null],
    ["샤프지수", m.sharpe, m.sharpe],
    ["거래일수", m.trading_days, null],
  ];
  const grid = document.getElementById("metrics");
  grid.innerHTML = "";
  items.forEach(([k, v, color]) => {
    let cls = "v";
    if (color != null && typeof color === "number") cls += color >= 0 ? " r-pass" : " reject";
    const d = document.createElement("div");
    d.className = "metric";
    d.innerHTML = `<div class="k">${k}</div><div class="${cls}">${v}</div>`;
    grid.appendChild(d);
  });
}

async function run() {
  const tickers = document
    .getElementById("tickers")
    .value.split(/[\s,]+/)
    .map((t) => t.trim())
    .filter(Boolean);

  if (!tickers.length) {
    setStatus("티커를 하나 이상 입력하세요.", true);
    return;
  }

  const payload = {
    tickers,
    period: document.getElementById("period").value,
    rebalance: document.getElementById("rebalance").value,
    initial_capital: Number(document.getElementById("initial").value) || 10000000,
    cost_rate: (Number(document.getElementById("cost").value) || 0) / 100,
  };

  document.getElementById("result").classList.add("hidden");
  setStatus("백테스트 실행 중... (기간/종목 수에 따라 수 초 소요)");

  try {
    const data = await PioneerAPI.backtest(payload);
    document.getElementById("status").classList.add("hidden");
    renderMetrics(data);
    document.getElementById("result").classList.remove("hidden");
    renderEquityChart("equityChart", data.equity_curve, "평가액");
  } catch (e) {
    setStatus(`백테스트 실패: ${e.message}`, true);
  }
}

document.getElementById("runBtn").addEventListener("click", run);
