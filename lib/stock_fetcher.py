from __future__ import annotations

import datetime
import json
import logging
import time
import urllib.request
from typing import Any

_LOGGER = logging.getLogger(__name__)
_ENDPOINT = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={range}"
_SYMBOL = "2308.TW"
_HTTP_TIMEOUT_SECONDS = 15
_HTTP_RETRIES = 2
_RETRY_BACKOFF_SECONDS = 1


class FetchError(Exception):
    def __init__(self, message: str, *, cause: BaseException | None = None):
        super().__init__(message)
        self.__cause__ = cause


class ValidationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def _request_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_err: BaseException | None = None
    for attempt in range(1, _HTTP_RETRIES + 2):
        try:
            with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError) as exc:
            last_err = exc
            _LOGGER.warning("fetch failed on attempt %s: %s", attempt, exc)
            if attempt < _HTTP_RETRIES + 1:
                time.sleep(_RETRY_BACKOFF_SECONDS)
    raise FetchError("HTTP request failed after retries", cause=last_err)


def _history_for(range_value: str, result: dict[str, Any]) -> list[dict[str, Any]] | None:
    timestamps = result.get("timestamp") or []
    quote_map = (result.get("indicators") or {}).get("quote") or [{}]
    quotes = quote_map[0] if quote_map else {}
    open_vals = quotes.get("open") or []
    high_vals = quotes.get("high") or []
    low_vals = quotes.get("low") or []
    close_vals = quotes.get("close") or []
    volume_vals = quotes.get("volume") or []
    hist: list[dict[str, Any]] = []
    for idx, ts in enumerate(timestamps):
        hist.append({
            "date": ts // 86400,
            "open": open_vals[idx] if idx < len(open_vals) else None,
            "high": high_vals[idx] if idx < len(high_vals) else None,
            "low": low_vals[idx] if idx < len(low_vals) else None,
            "close": close_vals[idx] if idx < len(close_vals) else None,
            "volume": volume_vals[idx] if idx < len(volume_vals) else None,
        })
    if not hist:
        return None
    if range_value == "1mo" and len(hist) > 22:
        return hist[-22:]
    return hist


def _transform(range_value: str, result: dict[str, Any]) -> dict[str, Any]:
    meta = result.get("meta") or {}
    history: dict[str, Any] = {"1mo": None, "1y": None}
    history[range_value] = _history_for(range_value, result)
    price = meta.get("regularMarketPrice")
    if price is None:
        last_bar = history[range_value][-1] if isinstance(history[range_value], list) and history[range_value] else {}
        price = last_bar.get("close") if isinstance(last_bar, dict) else None
        if price is None:
            raise ValidationError("missing regularMarketPrice")
    prev = meta.get("chartPreviousClose") or price
    change = float(price) - float(prev)
    pct = (change / float(prev) * 100) if prev else 0.0
    ts = meta.get("regularMarketTime") or (result.get("timestamp") or [0])[-1]
    if not ts:
        ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    return {
        "symbol": meta.get("symbol", _SYMBOL),
        "exchange": meta.get("exchangeName", "TAI"),
        "currency": meta.get("currency", "TWD"),
        "longName": meta.get("longName") or meta.get("shortName") or "",
        "previousClose": prev,
        "price": price,
        "open": meta.get("regularMarketOpen") if "regularMarketOpen" in meta else None,
        "dayHigh": meta.get("regularMarketDayHigh") if "regularMarketDayHigh" in meta else None,
        "dayLow": meta.get("regularMarketDayLow") if "regularMarketDayLow" in meta else None,
        "volume": meta.get("regularMarketVolume"),
        "change": change,
        "changePercent": pct,
        "fiftyTwoWeekHigh": meta.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": meta.get("fiftyTwoWeekLow"),
        "updatedAt": int(ts),
        "history": history,
    }


def _validate(payload: dict[str, Any], expected_history: tuple[str, ...] = ("1mo", "1y")) -> None:
    if payload.get("symbol") != _SYMBOL:
        raise ValidationError(f"unexpected symbol={payload.get('symbol')}")
    if payload.get("exchange") not in ("TPE", "TAI"):
        raise ValidationError(f"unexpected exchange={payload.get('exchange')}")
    if payload.get("currency") != "TWD":
        raise ValidationError(f"unexpected currency={payload.get('currency')}")
    if not isinstance(payload.get("longName"), str):
        raise ValidationError("missing longName")
    for field in ("previousClose", "price", "change", "changePercent", "fiftyTwoWeekHigh", "fiftyTwoWeekLow"):
        v = payload.get(field)
        if v is None or not isinstance(v, (int, float)):
            raise ValidationError(f"{field} must be numeric; got {v!r}")
    if not isinstance(payload.get("volume"), int) or payload.get("volume", 0) < 0:
        raise ValidationError(f"volume invalid: {payload.get('volume')!r}")
    if not isinstance(payload.get("updatedAt"), int) or payload.get("updatedAt", 0) <= 0:
        raise ValidationError(f"updatedAt invalid: {payload.get('updatedAt')!r}")
    hist = payload.get("history") or {}
    for range_ in expected_history:
        if not isinstance(hist.get(range_), list):
            raise ValidationError(f"history.{range_} missing or not an array")


def fetch(range_value: str) -> dict[str, Any]:
    if range_value not in ("1mo", "1y"):
        raise FetchError(f"unsupported range: {range_value}")
    payload = _request_json(_ENDPOINT.format(symbol=_SYMBOL, range=range_value))
    try:
        chart = payload["chart"]
        if chart.get("error"):
            raise FetchError(f"chart error: {chart['error']}", cause=ValueError(chart["error"]))
        result = chart["result"][0]
    except (KeyError, IndexError, TypeError) as err:
        raise FetchError("unexpected response shape", cause=err) from err
    data = _transform(range_value, result)
    _validate(data, expected_history=(range_value,))
    for key in ("1mo", "1y"):
        if key != range_value:
            data["history"][key] = None
    return data


def fetch_full_payload() -> dict[str, Any]:
    mo = _request_json(_ENDPOINT.format(symbol=_SYMBOL, range="1mo"))
    yr = _request_json(_ENDPOINT.format(symbol=_SYMBOL, range="1y"))
    for payload in (mo, yr):
        chart = payload["chart"]
        if chart.get("error"):
            raise FetchError(f"chart error: {chart['error']}", cause=ValueError(chart["error"]))
    result_mo = mo["chart"]["result"][0]
    result_yr = yr["chart"]["result"][0]
    data = _transform("1mo", result_mo)
    data["history"]["1y"] = _history_for("1y", result_yr)
    _validate(data, expected_history=("1mo", "1y"))
    return data


def fetch_single_payload() -> dict[str, Any]:
    return fetch("1mo")
