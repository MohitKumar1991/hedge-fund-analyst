"""Pure series/indicator primitives for the technical-analysis engine.

Every function is list -> list (aligned to input, None during warmup) and
depends only on the stdlib `math` — no state, no I/O. The analysis layer
(indicators.py) composes these; run it, not this module.
"""

import math

# ---------------------------------------------------------------------------
# series primitives (all return lists aligned to input, None during warmup)
# ---------------------------------------------------------------------------

def sma(vals, n):
    out = [None] * len(vals)
    acc = 0.0
    for i, v in enumerate(vals):
        acc += v
        if i >= n:
            acc -= vals[i - n]
        if i >= n - 1:
            out[i] = acc / n
    return out


def ema(vals, n, start=0):
    """EMA seeded with the SMA of the first n values from `start`."""
    out = [None] * len(vals)
    if len(vals) - start < n:
        return out
    seed = sum(vals[start:start + n]) / n
    out[start + n - 1] = seed
    k = 2.0 / (n + 1)
    for i in range(start + n, len(vals)):
        out[i] = vals[i] * k + out[i - 1] * (1 - k)
    return out


def wilder(vals, n, start=0):
    """Wilder smoothing (RSI/ATR convention): seed = mean of first n, then
    (prev*(n-1) + v) / n."""
    out = [None] * len(vals)
    if len(vals) - start < n:
        return out
    seed = sum(vals[start:start + n]) / n
    out[start + n - 1] = seed
    for i in range(start + n, len(vals)):
        out[i] = (out[i - 1] * (n - 1) + vals[i]) / n
    return out


def rolling_max(vals, n):
    out = [None] * len(vals)
    for i in range(n - 1, len(vals)):
        out[i] = max(vals[i - n + 1:i + 1])
    return out


def rolling_min(vals, n):
    out = [None] * len(vals)
    for i in range(n - 1, len(vals)):
        out[i] = min(vals[i - n + 1:i + 1])
    return out


def rolling_std(vals, n):
    out = [None] * len(vals)
    for i in range(n - 1, len(vals)):
        w = vals[i - n + 1:i + 1]
        m = sum(w) / n
        out[i] = math.sqrt(sum((x - m) ** 2 for x in w) / n)
    return out


# ---------------------------------------------------------------------------
# indicators
# ---------------------------------------------------------------------------

def rsi(closes, n):
    gains, losses = [0.0], [0.0]
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag = wilder(gains[1:], n)
    al = wilder(losses[1:], n)
    out = [None] * len(closes)
    for i in range(len(ag)):
        if ag[i] is None:
            continue
        if al[i] == 0:
            out[i + 1] = 100.0 if ag[i] > 0 else 50.0
        else:
            out[i + 1] = 100.0 - 100.0 / (1.0 + ag[i] / al[i])
    return out


def true_range(highs, lows, closes):
    tr = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr.append(max(highs[i] - lows[i],
                      abs(highs[i] - closes[i - 1]),
                      abs(lows[i] - closes[i - 1])))
    return tr


def atr(highs, lows, closes, n=14):
    return wilder(true_range(highs, lows, closes), n)


def macd(closes, fast=12, slow=26, sig=9):
    ef, es = ema(closes, fast), ema(closes, slow)
    line = [None if (a is None or b is None) else a - b for a, b in zip(ef, es)]
    first = next((i for i, v in enumerate(line) if v is not None), None)
    signal = [None] * len(closes)
    if first is not None:
        vals = line[first:]
        sig_part = ema(vals, sig)
        for i, v in enumerate(sig_part):
            signal[first + i] = v
    hist = [None if (a is None or b is None) else a - b for a, b in zip(line, signal)]
    return line, signal, hist


def bollinger(closes, n=20, k=2.0):
    mid = sma(closes, n)
    sd = rolling_std(closes, n)
    upper = [None if m is None else m + k * s for m, s in zip(mid, sd)]
    lower = [None if m is None else m - k * s for m, s in zip(mid, sd)]
    width = [None if (u is None or m in (None, 0)) else (u - l) / m
             for u, l, m in zip(upper, lower, mid)]
    pctb = [None if (u is None or u == l) else (c - l) / (u - l)
            for c, u, l in zip(closes, upper, lower)]
    return mid, upper, lower, width, pctb


def donchian(highs, lows, n=20):
    """Prior-window channel (excludes the current bar) so a close above
    `hi` is a genuine Turtle-style breakout, with no lookahead."""
    hi = [None] * len(highs)
    lo = [None] * len(lows)
    for i in range(n, len(highs)):
        hi[i] = max(highs[i - n:i])
        lo[i] = min(lows[i - n:i])
    return hi, lo


def adx(highs, lows, closes, n=14):
    m = len(closes)
    plus_dm, minus_dm = [0.0], [0.0]
    for i in range(1, m):
        up = highs[i] - highs[i - 1]
        dn = lows[i - 1] - lows[i]
        plus_dm.append(up if (up > dn and up > 0) else 0.0)
        minus_dm.append(dn if (dn > up and dn > 0) else 0.0)
    tr = true_range(highs, lows, closes)
    sp = wilder(plus_dm[1:], n)
    sm = wilder(minus_dm[1:], n)
    st = wilder(tr[1:], n)
    pdi = [None] * m
    mdi = [None] * m
    dx = []
    for i in range(len(sp)):
        if sp[i] is None or st[i] in (None, 0):
            dx.append(None)
            continue
        p = 100.0 * sp[i] / st[i]
        q = 100.0 * sm[i] / st[i]
        pdi[i + 1], mdi[i + 1] = p, q
        dx.append(100.0 * abs(p - q) / (p + q) if (p + q) > 0 else 0.0)
    first = next((i for i, v in enumerate(dx) if v is not None), None)
    out = [None] * m
    if first is not None and len(dx) - first >= n:
        w = wilder(dx[first:], n)
        for i, v in enumerate(w):
            out[first + i + 1] = v
    return out, pdi, mdi


def obv(closes, volumes):
    out = [0.0]
    for i in range(1, len(closes)):
        v = volumes[i] or 0
        if closes[i] > closes[i - 1]:
            out.append(out[-1] + v)
        elif closes[i] < closes[i - 1]:
            out.append(out[-1] - v)
        else:
            out.append(out[-1])
    return out


def supertrend(highs, lows, closes, n=10, mult=3.0):
    """Returns (line, direction) — direction +1 long / -1 short."""
    a = atr(highs, lows, closes, n)
    m = len(closes)
    line = [None] * m
    direction = [None] * m
    fu = [None] * m  # final upper band
    fl = [None] * m  # final lower band
    for i in range(m):
        if a[i] is None:
            continue
        hl2 = (highs[i] + lows[i]) / 2.0
        bu = hl2 + mult * a[i]
        bl = hl2 - mult * a[i]
        pu, pl = fu[i - 1] if i else None, fl[i - 1] if i else None
        fu[i] = bu if (pu is None or bu < pu or closes[i - 1] > pu) else pu
        fl[i] = bl if (pl is None or bl > pl or closes[i - 1] < pl) else pl
        prev_dir = direction[i - 1] if i and direction[i - 1] is not None else 1
        if prev_dir == 1:
            direction[i] = -1 if closes[i] < fl[i] else 1
        else:
            direction[i] = 1 if closes[i] > fu[i] else -1
        line[i] = fl[i] if direction[i] == 1 else fu[i]
    return line, direction


def chandelier(highs, lows, closes, atr_vals, n=22, mult=3.0):
    """Long/short trailing exits: highest close - k*ATR / lowest close + k*ATR."""
    hi_close = rolling_max(closes, n)
    lo_close = rolling_min(closes, n)
    long_exit = [None if (h is None or a is None) else h - mult * a
                 for h, a in zip(hi_close, atr_vals)]
    short_exit = [None if (l is None or a is None) else l + mult * a
                  for l, a in zip(lo_close, atr_vals)]
    return long_exit, short_exit


def last_pivot(vals, span=2, kind="low"):
    """Most recent confirmed fractal pivot (needs `span` bars on each side)."""
    cmp = (lambda a, b: a <= b) if kind == "low" else (lambda a, b: a >= b)
    for i in range(len(vals) - span - 1, span - 1, -1):
        window = vals[i - span:i] + vals[i + 1:i + span + 1]
        if all(cmp(vals[i], w) for w in window):
            return vals[i]
    return None
