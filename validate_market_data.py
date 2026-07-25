#!/usr/bin/env python3
"""Validate the integrated public market-data flow for TPE:2308."""

from __future__ import annotations

import json
import sys
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from typing import Any

REQUIRED = [
    "regularMarketPrice",
    "chartPreviousClose",
    "regularMarketDayHigh",
    "regularMarketDayLow",
    "regularMarketVolume",
    "fiftyTwoWeekHigh",
    "fiftyTwoWeekLow",
]
HOSTS = [
    "https://query2.finance.yahoo.com",
    "https://query1.finance.yahoo.com",
]


def fetch(url: str) -> dict[str, Any]:
    req = urllib_request.Request(url, headers={"User-Agent": "Mozilla/5.0 (TPE-2308-validator)"})
    with urllib_request.urlopen(req, timeout=30) as response:
        return dict(json.loads(response.read().decode()))


def extract(url: str) -> dict[str, Any]:
    payload = fetch(url)
    chart: dict[str, Any] = payload.get("chart") or {}
    result_list = chart.get("result") or [{}]
    result = next(iter(result_list))
    if not result:
        raise ValueError("chart.result is empty")
    return result


def validate(result: dict[str, Any]) -> dict[str, object]:
    meta: dict[str, Any] = result.get("meta") or {}
    missing = [name for name in REQUIRED if not isinstance(meta.get(name), (int, float))]
    quote_list = ((result.get("indicators") or {}).get("quote") or [{}])
    quote = next(iter(quote_list), {})
    bad_series = {
        name: len(series)
        for name, series in quote.items()
        if not isinstance(series, list) or not series
    }
    ts: list[int] = list(result.get("timestamp") or [])
    close_series = quote.get("close") or []
    return {
        "metaKeysOk": not missing,
        "missing": missing,
        "seriesCounts": bad_series,
        "seriesLen": len(ts),
        "lastClose": close_series[-1] if close_series else None,
        "lastTs": ts[-1] if ts else None,
    }


def main() -> int:
    findings: list[dict[str, object]] = []
    for host in HOSTS:
        url = f"{host}/v8/finance/chart/2308.TW?range=1mo&interval=1d"
        try:
            result = extract(url)
            data = validate(result)
            data["url"] = url
            findings.append({"host": urlparse(host).netloc, "status": "ok", "data": data})
            break
        except (HTTPError, URLError, OSError, ValueError, TypeError) as exc:
            findings.append(
                {
                    "host": urlparse(host).netloc,
                    "status": "failed",
                    "error": str(exc),
                    "type": type(exc).__name__,
                }
            )

    report = {
        "markets": findings,
        "requirementsMet": all(item.get("data", {}).get("metaKeysOk") for item in findings),
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["requirementsMet"] else 2


if __name__ == "__main__":
    sys.exit(main())
