// chart.js — Chart.js 래퍼 (가격 / 자산곡선 라인 차트)
let _priceChart = null;
let _equityChart = null;

// 자산곡선(백테스트) 렌더링. points: [{date, value}]
function renderEquityChart(canvasId, points, label) {
  const ctx = document.getElementById(canvasId).getContext("2d");
  if (_equityChart) _equityChart.destroy();
  _equityChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: points.map((p) => p.date),
      datasets: [
        {
          label: label || "포트폴리오 평가액",
          data: points.map((p) => p.value),
          borderColor: "#17a34a",
          backgroundColor: "rgba(23,163,74,0.08)",
          borderWidth: 2,
          pointRadius: 0,
          fill: true,
          tension: 0.1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 8, color: "#8a94a6" }, grid: { display: false } },
        y: {
          ticks: {
            color: "#8a94a6",
            callback: (v) => (v / 1e6).toLocaleString("ko-KR", { maximumFractionDigits: 1 }) + "M",
          },
          grid: { color: "rgba(0,0,0,0.05)" },
        },
      },
    },
  });
}

function renderPriceChart(canvasId, prices, label) {
  const ctx = document.getElementById(canvasId).getContext("2d");
  const labels = prices.map((p) => p.date);
  const closes = prices.map((p) => p.close);

  if (_priceChart) _priceChart.destroy();

  _priceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: label || "종가",
          data: closes,
          borderColor: "#2f6df6",
          backgroundColor: "rgba(47,109,246,0.08)",
          borderWidth: 2,
          pointRadius: 0,
          fill: true,
          tension: 0.15,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 8, color: "#8a94a6" }, grid: { display: false } },
        y: { ticks: { color: "#8a94a6" }, grid: { color: "rgba(0,0,0,0.05)" } },
      },
    },
  });
}
