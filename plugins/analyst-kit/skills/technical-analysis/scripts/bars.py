"""OHLCV bar handling for the technical-analysis engine: load + adjust an
FMP-style or plain JSON price file, resample daily bars to weekly/monthly,
and convert dates for datetime chart axes. No indicator math lives here."""

import datetime
import json


def load_bars(path, adjust=True):
    with open(path) as f:
        raw = json.load(f)
    if isinstance(raw, dict):
        raw = raw.get("historical") or raw.get("data") or []
    bars = []
    for r in raw:
        if r.get("close") is None or r.get("date") is None:
            continue
        o, h, l, c = (float(r.get(k, r["close"]) or r["close"])
                      for k in ("open", "high", "low", "close"))
        adj = r.get("adjClose")
        if adjust and adj is not None and c:
            f_ = float(adj) / c
            o, h, l, c = o * f_, h * f_, l * f_, float(adj)
        bars.append({"date": str(r["date"])[:10], "open": o, "high": h,
                     "low": l, "close": c,
                     "volume": float(r.get("volume") or 0)})
    seen = {}
    for b in bars:
        seen[b["date"]] = b  # last wins on duplicate dates
    return sorted(seen.values(), key=lambda b: b["date"])


def _ymd(date_str):
    y, m, d = (int(x) for x in date_str.split("-"))
    return y, m, d


def _iso_week(date_str):
    y, m, d = _ymd(date_str)
    iso = datetime.date(y, m, d).isocalendar()
    return iso[0], iso[1]


def resample(bars, timeframe):
    """daily bars -> weekly (ISO week) or monthly. Bar date = last trading day."""
    if timeframe == "daily":
        return bars
    key = _iso_week if timeframe == "weekly" else (lambda d: _ymd(d)[:2])
    out, cur, cur_key = [], None, None
    for b in bars:
        k = key(b["date"])
        if k != cur_key:
            if cur:
                out.append(cur)
            cur = dict(b)
            cur_key = k
        else:
            cur["high"] = max(cur["high"], b["high"])
            cur["low"] = min(cur["low"], b["low"])
            cur["close"] = b["close"]
            cur["volume"] += b["volume"]
            cur["date"] = b["date"]
    if cur:
        out.append(cur)
    return out


def to_millis(date_str):
    y, m, d = _ymd(date_str)
    return int(datetime.datetime(y, m, d, tzinfo=datetime.timezone.utc).timestamp() * 1000)
