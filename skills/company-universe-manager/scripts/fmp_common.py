"""Shared FMP plumbing for this skill's fetch scripts (monitor_dates, fetch_news).

Pure standard library.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

FMP_BASE = "https://financialmodelingprep.com/api/v3"


def http_json(url: str, timeout: int = 20) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "company-universe-manager"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted FMP host)
        return json.loads(resp.read().decode("utf-8"))
