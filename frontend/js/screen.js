// screen.js — 퀀트 스크리닝 페이지 로직

function num(id) {
  const v = document.getElementById(id).value.trim();
  return v === "" ? null : Number(v);
}

function fmt(v, d = 2) {
  if (v === null || v === undefined) return "—";
  return Number(v).toLocaleString("ko-KR", { maximumFractionDigits: d });
}

function fmtCap(v, currency) {
  if (v === null || v === undefined) return "—";
  const unit = currency === "USD" ? 1e9 : 1e12;
  const label = currency === "USD" ? "B" : "조";
  return (v / unit).toLocaleString("ko-KR", { maximumFractionDigits: 1 }) + label;
}

function setStatus(msg, isError = false) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = "status" + (isError ? " error" : "");
  el.classList.remove("hidden");
}

function renderResults(data) {
  document.getElementById("status").classList.add("hidden");
  document.getElementById("summary").textContent =
    `전체 ${data.total}종목 중 조건 통과 ${data.passed}종목`;

  let html = `<table class="fin"><thead><tr>
    <th>결과</th><th>티커</th><th>종목명</th><th>현재가</th>
    <th>PER</th><th>PBR</th><th>ROE</th><th>배당%</th><th>시총</th><th>비고</th>
  </tr></thead><tbody>`;

  data.results.forEach((r) => {
    if (!r.ok) {
      html += `<tr><td class="r-fail">에러</td><td>${r.ticker}</td>
        <td colspan="8" class="reject">${r.error || "조회 실패"}</td></tr>`;
      return;
    }
    const badge = r.passed
      ? `<span class="r-pass">✔ 통과</span>`
      : `<span class="r-fail">✘ 탈락</span>`;
    const note = r.passed ? "" : r.reasons.join(", ");
    html += `<tr>
      <td class="${r.passed ? "r-pass" : "r-fail"}">${badge}</td>
      <td>${r.ticker}</td>
      <td style="text-align:left">${r.name || "—"}</td>
      <td>${fmt(r.price, r.currency === "KRW" ? 0 : 2)}</td>
      <td>${fmt(r.per)}</td>
      <td>${fmt(r.pbr)}</td>
      <td>${r.roe != null ? fmt(r.roe) + "%" : "—"}</td>
      <td>${r.dividend_yield != null ? fmt(r.dividend_yield) + "%" : "—"}</td>
      <td>${fmtCap(r.market_cap, r.currency)}</td>
      <td style="text-align:left" class="reject">${note}</td>
    </tr>`;
  });
  html += "</tbody></table>";
  document.getElementById("table").innerHTML = html;
  document.getElementById("result").classList.remove("hidden");
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

  const filters = {
    per_max: num("per_max"),
    pbr_max: num("pbr_max"),
    roe_min: num("roe_min"),
    dividend_min: num("dividend_min"),
  };

  document.getElementById("result").classList.add("hidden");
  setStatus(`${tickers.length}종목 스크리닝 중... (종목이 많으면 수 초 소요)`);

  try {
    const data = await PioneerAPI.screen(tickers, filters);
    renderResults(data);
  } catch (e) {
    setStatus(`스크리닝 실패: ${e.message}`, true);
  }
}

document.getElementById("runBtn").addEventListener("click", run);
