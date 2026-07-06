// app.js — index.html 페이지 로직 (종목 조회 + 재무 표시)

function fmtNum(v, digits = 2) {
  if (v === null || v === undefined) return "—";
  return Number(v).toLocaleString("ko-KR", { maximumFractionDigits: digits });
}

function fmtMoney(v, currency) {
  if (v === null || v === undefined) return "—";
  const symbol = currency === "USD" ? "$" : currency === "KRW" ? "₩" : "";
  return symbol + fmtNum(v, currency === "KRW" ? 0 : 2);
}

function fmtCap(v, currency) {
  if (v === null || v === undefined) return "—";
  const unit = currency === "USD" ? 1e9 : 1e12;
  const label = currency === "USD" ? "B" : "조";
  return (v / unit).toLocaleString("ko-KR", { maximumFractionDigits: 2 }) + label;
}

function setStatus(msg, isError = false) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = "status" + (isError ? " error" : "");
  el.classList.remove("hidden");
}

function renderStock(info) {
  document.getElementById("stName").textContent = info.name;
  document.getElementById("stTicker").textContent = info.ticker;
  document.getElementById("stPrice").textContent = fmtMoney(info.price, info.currency);

  const changeEl = document.getElementById("stChange");
  if (info.price != null && info.previous_close != null) {
    const diff = info.price - info.previous_close;
    const pct = (diff / info.previous_close) * 100;
    const up = diff >= 0;
    changeEl.className = "change " + (up ? "up" : "down");
    changeEl.textContent = `${up ? "▲" : "▼"} ${fmtNum(Math.abs(diff), info.currency === "KRW" ? 0 : 2)} (${pct.toFixed(2)}%)`;
  } else {
    changeEl.textContent = "";
  }

  const tags = document.getElementById("stTags");
  tags.innerHTML = "";
  [info.market === "KR" ? "한국" : "미국", info.sector, info.industry]
    .filter(Boolean)
    .forEach((t) => {
      const s = document.createElement("span");
      s.className = "tag";
      s.textContent = t;
      tags.appendChild(s);
    });

  const metrics = [
    ["PER", fmtNum(info.per)],
    ["선행 PER", fmtNum(info.forward_per)],
    ["PBR", fmtNum(info.pbr)],
    ["ROE", info.roe != null ? fmtNum(info.roe) + "%" : "—"],
    ["EPS", fmtNum(info.eps)],
    ["배당수익률", info.dividend_yield != null ? fmtNum(info.dividend_yield) + "%" : "—"],
    ["시가총액", fmtCap(info.market_cap, info.currency)],
    ["52주 최고", fmtMoney(info.fifty_two_week_high, info.currency)],
    ["52주 최저", fmtMoney(info.fifty_two_week_low, info.currency)],
  ];
  const grid = document.getElementById("stMetrics");
  grid.innerHTML = "";
  metrics.forEach(([k, v]) => {
    const d = document.createElement("div");
    d.className = "metric";
    d.innerHTML = `<div class="k">${k}</div><div class="v">${v}</div>`;
    grid.appendChild(d);
  });
}

function renderIncome(fin, currency) {
  const wrap = document.getElementById("incomeTable");
  const rows = fin.income_statement || [];
  if (!rows.length) {
    wrap.innerHTML = '<div class="status">재무 데이터가 없습니다.</div>';
    return;
  }
  // 주요 항목만 추출
  const keys = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income"];
  const periods = rows.map((r) => (r.period || "").slice(0, 4));
  let html = "<table class='fin'><thead><tr><th>항목</th>";
  periods.forEach((p) => (html += `<th>${p}</th>`));
  html += "</tr></thead><tbody>";
  keys.forEach((k) => {
    if (!rows.some((r) => r[k] != null)) return;
    html += `<tr><td>${k}</td>`;
    rows.forEach((r) => {
      const v = r[k];
      html += `<td>${v != null ? fmtCap(v, currency) : "—"}</td>`;
    });
    html += "</tr>";
  });
  html += "</tbody></table>";
  wrap.innerHTML = html;
}

async function loadStock(ticker) {
  ticker = (ticker || "").trim();
  if (!ticker) return;
  hideSuggestions();
  document.getElementById("tickerInput").value = ticker;
  setStatus(`'${ticker}' 조회 중...`);
  document.getElementById("result").classList.add("hidden");

  try {
    const info = await PioneerAPI.getStock(ticker);
    renderStock(info);
    document.getElementById("status").classList.add("hidden");
    document.getElementById("result").classList.remove("hidden");

    // 차트/재무는 병렬 로드 (실패해도 기본정보는 유지)
    PioneerAPI.getHistory(ticker, "1y")
      .then((h) => renderPriceChart("priceChart", h.prices, info.name))
      .catch((e) => console.warn("history 실패:", e.message));
    PioneerAPI.getFinancials(ticker)
      .then((f) => renderIncome(f, info.currency))
      .catch((e) => console.warn("financials 실패:", e.message));
    return true;
  } catch (e) {
    setStatus(`조회 실패: ${e.message}`, true);
    return false;
  }
}

// ── 검색 자동완성 ─────────────────────────────────────────────
const inputEl = document.getElementById("tickerInput");
const sugEl = document.getElementById("suggestions");
let sugItems = [];   // 현재 표시 중인 후보
let sugActive = -1;  // 키보드로 선택된 인덱스
let debounceId = null;

// 티커처럼 보이면(6자리 코드 또는 영문 심볼) 검색 없이 바로 조회 가능
function isTickerLike(q) {
  return /^\d{6}(\.(ks|kq))?$/i.test(q) || /^[A-Za-z][A-Za-z.\-]{0,6}$/.test(q);
}
function hasKorean(q) {
  return /[가-힣]/.test(q);
}

function hideSuggestions() {
  sugEl.classList.add("hidden");
  sugEl.innerHTML = "";
  sugItems = [];
  sugActive = -1;
}

function renderSuggestions(results) {
  sugItems = results;
  sugActive = -1;
  if (!results.length) {
    sugEl.innerHTML = '<li class="s-empty">검색 결과가 없습니다.</li>';
    sugEl.classList.remove("hidden");
    return;
  }
  sugEl.innerHTML = results
    .map(
      (r, i) => `<li data-idx="${i}">
        <span class="s-name">${r.name}</span>
        <span class="s-badge">${r.market === "KR" ? r.exchange : "US"}</span>
        <span class="s-ticker">${r.ticker}</span>
      </li>`
    )
    .join("");
  sugEl.classList.remove("hidden");
  sugEl.querySelectorAll("li[data-idx]").forEach((li) =>
    li.addEventListener("mousedown", (e) => {
      e.preventDefault(); // blur 방지
      loadStock(sugItems[Number(li.dataset.idx)].ticker);
    })
  );
}

async function runSearch(q) {
  try {
    const data = await PioneerAPI.searchStock(q, 15);
    renderSuggestions(data.results || []);
  } catch (e) {
    console.warn("검색 실패:", e.message);
    hideSuggestions();
  }
}

function setActive(idx) {
  const lis = sugEl.querySelectorAll("li[data-idx]");
  if (!lis.length) return;
  sugActive = (idx + lis.length) % lis.length;
  lis.forEach((li, i) => li.classList.toggle("active", i === sugActive));
}

// 입력 시 디바운스 검색 (한글은 1자, 영문은 2자 이상부터)
inputEl.addEventListener("input", () => {
  const q = inputEl.value.trim();
  clearTimeout(debounceId);
  if ((q.length < 2 && !hasKorean(q)) || /^\d{6}\.(ks|kq)$/i.test(q)) {
    hideSuggestions();
    return;
  }
  debounceId = setTimeout(() => runSearch(q), 250);
});

inputEl.addEventListener("keydown", (e) => {
  const open = !sugEl.classList.contains("hidden") && sugItems.length;
  if (e.key === "ArrowDown" && open) {
    e.preventDefault();
    setActive(sugActive + 1);
  } else if (e.key === "ArrowUp" && open) {
    e.preventDefault();
    setActive(sugActive - 1);
  } else if (e.key === "Enter") {
    e.preventDefault();
    if (open && sugActive >= 0) loadStock(sugItems[sugActive].ticker);
    else submitSearch();
  } else if (e.key === "Escape") {
    hideSuggestions();
  }
});

inputEl.addEventListener("blur", () => setTimeout(hideSuggestions, 150));

// 조회 버튼: 티커면 바로 조회, 아니면 이름 검색
async function submitSearch() {
  const q = inputEl.value.trim();
  if (!q) return;
  // 티커처럼 보이면 먼저 직접 조회 시도, 실패하면 이름 검색으로 폴백
  if (isTickerLike(q) && !hasKorean(q)) {
    const ok = await loadStock(q);
    if (ok) return;
  }
  // 이름 검색 → 결과 1개면 바로 조회, 여러 개면 후보 표시
  setStatus(`'${q}' 검색 중...`);
  try {
    const data = await PioneerAPI.searchStock(q, 15);
    const results = data.results || [];
    document.getElementById("status").classList.add("hidden");
    if (results.length === 1) {
      loadStock(results[0].ticker);
    } else if (results.length > 1) {
      renderSuggestions(results);
      setStatus(`'${q}' 관련 ${results.length}개 종목 — 아래에서 선택하세요.`);
    } else {
      setStatus(`'${q}' 검색 결과가 없습니다.`, true);
    }
  } catch (e) {
    setStatus(`검색 실패: ${e.message}`, true);
  }
}

document.getElementById("searchBtn").addEventListener("click", submitSearch);

// 초기 로드 시 기본 티커 조회
loadStock("AAPL");
