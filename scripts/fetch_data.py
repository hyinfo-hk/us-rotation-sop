#!/usr/bin/env python3
"""Pull US index + 11 sector ETF stats for the SOP page. No API key."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

HKT = timezone(timedelta(hours=8))

INDEX_MAP = [
    ("標普500", "SPX", "^GSPC"),
    ("納斯達克綜合", "COMP", "^IXIC"),
    ("道瓊斯工業", "DJIA", "^DJI"),
    ("羅素2000", "RUT", "^RUT"),
    ("納指100", "NDX", "^NDX"),
    ("費半 SOX", "SOX", "^SOX"),
]
ETF_TICKERS = ["SPY", "QQQ", "DIA", "IWM", "RSP", "SOXX"]
SECTORS = [
    ("XLK", "科技", 5, 2, "後期教科書唔領先，AI capex +2"),
    ("XLE", "能源", 9, 0, "擴張後期理論領先"),
    ("XLV", "醫療", 6, 0, "後期中性偏防禦"),
    ("XLB", "原物料", 8, -1, "理論領先，近月未確認"),
    ("XLF", "金融", 5, -1, "再加息預期壓抑"),
    ("XLI", "工業", 5, 0, "中期領先、後期轉中性"),
    ("XLP", "必需消費", 6, 0, "後期／衰退初期防禦"),
    ("XLC", "通訊", 4, 0, "早周期領先，後期偏落後"),
    ("XLRE", "房地產", 4, 0, "高利率環境落後"),
    ("XLY", "非必需消費", 3, 0, "早周期領先，後期落後"),
    ("XLU", "公用", 6, -1, "防禦中性，利率打壓"),
]


def last_session(now: datetime) -> datetime:
    d = now.astimezone(HKT)
    # before US open (~21:30 HKT) use previous session
    if d.hour < 21 or (d.hour == 21 and d.minute < 30):
        d = d - timedelta(days=1)
    while d.weekday() >= 5:
        d = d - timedelta(days=1)
    return d


def ret(series: pd.Series, days: int) -> float | None:
    if series is None or series.empty:
        return None
    last = float(series.iloc[-1])
    target = series.index[-1] - pd.Timedelta(days=days)
    prev = series[series.index <= target]
    if prev.empty:
        return None
    return round((last / float(prev.iloc[-1]) - 1) * 100, 2)


def pack_bar(hist: pd.DataFrame) -> dict | None:
    if hist is None or hist.empty:
        return None
    close = hist["Close"].dropna()
    high = hist["High"].dropna()
    low = hist["Low"].dropna()
    last = float(close.iloc[-1])
    prev = float(close.iloc[-2]) if len(close) > 1 else last
    ytd_base = close[close.index.year < close.index[-1].year]
    ytd = round((last / float(ytd_base.iloc[-1]) - 1) * 100, 2) if len(ytd_base) else None
    last21 = hist.tail(22)
    last20c = close.tail(20)
    hi52 = float(high.max())
    return {
        "c": round(last, 2),
        "d1": round((last / prev - 1) * 100, 2),
        "w1": ret(close, 7),
        "m1": ret(close, 30),
        "m3": ret(close, 90),
        "ytd": ytd,
        "y1": ret(close, 365),
        "hi52": round(hi52, 2),
        "pct": round((last / hi52 - 1) * 100, 2) if hi52 else None,
        "lo1m": round(float(last21["Low"].min()), 2),
        "hi1m": round(float(last21["High"].max()), 2),
        "hi3m": round(float(hist.tail(66)["High"].max()), 2),
        "sma20": round(float(last20c.mean()), 2) if len(last20c) else None,
        "date": close.index[-1].strftime("%Y-%m-%d"),
    }


def download(tickers: list[str]) -> dict[str, pd.DataFrame]:
    data = yf.download(
        tickers=tickers,
        period="15mo",
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )
    out = {}
    if len(tickers) == 1:
        out[tickers[0]] = data
        return out
    for t in tickers:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if t in data.columns.get_level_values(0):
                    out[t] = data[t].dropna(how="all")
                elif t in data.columns.get_level_values(1):
                    out[t] = data.xs(t, axis=1, level=1).dropna(how="all")
            else:
                out[t] = data
        except Exception:
            pass
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/latest.json")
    args = parser.parse_args()

    now = datetime.now(HKT)
    sess = last_session(now)
    all_t = [x[2] for x in INDEX_MAP] + ["^VIX"] + ETF_TICKERS + [s[0] for s in SECTORS]
    frames = download(all_t)

    indices = []
    for name, code, ticker in INDEX_MAP:
        bar = pack_bar(frames.get(ticker))
        if not bar:
            continue
        indices.append({"name": name, "code": code, **bar})

    vix_bar = pack_bar(frames.get("^VIX")) or {"c": None, "d1": None, "w1": None}

    etf = {}
    for t in ETF_TICKERS:
        bar = pack_bar(frames.get(t))
        if bar:
            etf[t] = bar

    sectors = []
    for ticker, name, tbase, tadj, why in SECTORS:
        bar = pack_bar(frames.get(ticker))
        if not bar:
            continue
        sectors.append({
            "id": ticker,
            "name": name,
            "tBase": tbase,
            "tAdj": tadj,
            "tWhy": why,
            "c": bar["c"],
            "d1": bar["d1"],
            "w1": bar["w1"],
            "m1": bar["m1"],
            "m3": bar["m3"],
            "ytd": bar["ytd"],
            "y1": bar["y1"],
            "lo1m": bar["lo1m"],
            "sma20": bar["sma20"],
            "hi1m": bar["hi1m"],
            "hi3m": bar["hi3m"],
            "flow": 5,
        })

    missing = []
    if len(indices) < 5:
        missing.append("indices")
    if not etf.get("SPY"):
        missing.append("SPY")
    if len(sectors) < 11:
        missing.append(f"sectors {len(sectors)}/11")

    payload = {
        "schema": "us-rotation-sop/v1",
        "calendar_date": now.strftime("%Y-%m-%d"),
        "session_date": sess.strftime("%Y-%m-%d"),
        "generated_at": now.isoformat(),
        "source": "github-actions-yfinance",
        "vix": {"c": vix_bar.get("c"), "d1": vix_bar.get("d1"), "w1": vix_bar.get("w1")},
        "indices": indices,
        "etf": etf,
        "sectors": sectors,
        "macro": {
            "items": [
                ["提示", "宏觀欄請用 FRED／BLS 最新公布核對；此腳本只保證價"],
            ],
            "events": "由 GitHub Actions 自動更新報價。宏觀與事件請對照當日新聞。",
        },
        "note": "自動報價快照。缺項: " + (", ".join(missing) if missing else "無"),
        "data_ok": not missing,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", out, "session", payload["session_date"], "ok", payload["data_ok"])


if __name__ == "__main__":
    main()
