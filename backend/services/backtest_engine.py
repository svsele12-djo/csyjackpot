"""
backtest_engine.py — 동일비중 포트폴리오 백테스트 엔진.

전략: 입력된 티커들을 동일비중으로 매수 후, 지정 주기로 리밸런싱.
거래비용(기본 0.3%)을 매매 회전율에 비례해 차감한다.

주의: 서로 다른 통화(원/달러)의 종목을 섞으면 환율은 무시하고
각 종목의 수익률(pct_change)만으로 합성한다. 데모용 단순화이므로
실제 투자 판단에는 통화 통일이 필요하다.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from services import data_fetcher


def _rebalance_flags(index: pd.DatetimeIndex, freq: str) -> pd.Series:
    """리밸런싱 발생일에 True. freq: none/monthly/quarterly/yearly."""
    flags = pd.Series(False, index=index)
    if freq == "none":
        return flags
    period_map = {"monthly": "M", "quarterly": "Q", "yearly": "Y"}
    code = period_map.get(freq)
    if code is None:
        return flags
    # 각 기간의 마지막 거래일에 리밸런싱
    grp = pd.Series(index.to_period(code), index=index)
    last_days = grp.groupby(grp).apply(lambda s: s.index[-1])
    flags.loc[last_days.values] = True
    return flags


def _build_price_frame(tickers: list[str], period: str) -> pd.DataFrame:
    """티커별 종가 시계열을 하나의 DataFrame으로 정렬."""
    series = {}
    for t in tickers:
        hist = data_fetcher.get_price_history(t, period=period, interval="1d")
        if not hist:
            continue
        s = pd.Series(
            {row["date"]: row["close"] for row in hist if row.get("close") is not None}
        )
        if not s.empty:
            series[t] = s
    if not series:
        return pd.DataFrame()
    df = pd.DataFrame(series)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index().ffill().dropna()
    return df


def run_backtest(
    tickers: list[str],
    period: str = "3y",
    rebalance: str = "quarterly",
    initial_capital: float = 10_000_000,
    cost_rate: float = 0.003,
) -> dict[str, Any]:
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    tickers = list(dict.fromkeys(tickers))  # 중복 제거, 순서 유지
    if not tickers:
        raise ValueError("티커를 하나 이상 입력하세요.")

    prices = _build_price_frame(tickers, period)
    if prices.empty or len(prices) < 2:
        raise ValueError("가격 데이터가 부족합니다. 티커/기간을 확인하세요.")

    used = list(prices.columns)
    n = len(used)
    w_target = np.full(n, 1.0 / n)
    rets = prices.pct_change().fillna(0.0)
    reb = _rebalance_flags(prices.index, rebalance)

    dates = prices.index
    # 초기 매수: 전액 매수 비용 차감
    value = initial_capital * (1 - cost_rate)
    pos = value * w_target  # 자산별 평가액

    equity_curve = []
    daily_port_rets = []
    prev_value = value

    for i, date in enumerate(dates):
        if i > 0:
            pos = pos * (1.0 + rets.iloc[i].values)
        value = float(pos.sum())
        daily_port_rets.append(value / prev_value - 1.0 if prev_value else 0.0)
        prev_value = value

        # 리밸런싱 (마지막 날 제외)
        if reb.iloc[i] and i != len(dates) - 1 and value > 0:
            target = value * w_target
            traded = float(np.abs(target - pos).sum())
            cost = traded * cost_rate
            value -= cost
            pos = value * w_target
            prev_value = value

        equity_curve.append({"date": date.strftime("%Y-%m-%d"), "value": round(value, 2)})

    metrics = _metrics(equity_curve, daily_port_rets, initial_capital)

    return {
        "tickers": used,
        "period": period,
        "rebalance": rebalance,
        "initial_capital": initial_capital,
        "cost_rate": cost_rate,
        "start": equity_curve[0]["date"],
        "end": equity_curve[-1]["date"],
        "equity_curve": equity_curve,
        "metrics": metrics,
    }


def _metrics(equity_curve, daily_rets, initial_capital) -> dict[str, Any]:
    values = np.array([e["value"] for e in equity_curve], dtype=float)
    final = float(values[-1])
    total_return = final / initial_capital - 1.0

    days = len(values)
    years = days / 252.0 if days else 0.0
    cagr = (final / initial_capital) ** (1.0 / years) - 1.0 if years > 0 and final > 0 else 0.0

    # 최대낙폭(MDD)
    running_max = np.maximum.accumulate(values)
    drawdowns = values / running_max - 1.0
    mdd = float(drawdowns.min()) if len(drawdowns) else 0.0

    r = np.array(daily_rets, dtype=float)
    vol = float(r.std(ddof=1) * np.sqrt(252)) if len(r) > 1 else 0.0
    ann_ret = float(r.mean() * 252) if len(r) else 0.0
    sharpe = ann_ret / vol if vol > 0 else 0.0

    return {
        "final_value": round(final, 2),
        "total_return_pct": round(total_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(mdd * 100, 2),
        "volatility_pct": round(vol * 100, 2),
        "sharpe": round(sharpe, 2),
        "trading_days": days,
    }
