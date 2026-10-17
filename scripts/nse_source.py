"""
nse_source.py - download and normalise NSE end-of-day bhavcopy files.

Two eras are handled automatically:
  * Modern (UDiFF / SEBI CMTS), from 2024-07-08 onward:
        https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip
        https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip
  * Legacy, up to 2024-07-05:
        https://archives.nseindia.com/content/historical/EQUITIES/YYYY/MMM/cmDDmmmYYYYbhav.csv.zip
        https://archives.nseindia.com/content/historical/DERIVATIVES/YYYY/MMM/foDDmmmYYYYbhav.csv.zip

No login, no API key, no cookies are required - a browser-like User-Agent is enough.
Only trading days exist; weekends and exchange holidays return 404 and are skipped.

This is a plain downloader. It does NOT redistribute data. NSE/BSE data is subject to
their Data Sharing & Usage Policy - personal use is fine, public redistribution may
require a licence.
"""

from __future__ import annotations

import io
import time
import zipfile
from dataclasses import dataclass
from datetime import date

import pandas as pd
import requests

UDIFF_CUTOVER = date(2024, 7, 8)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "*/*",
}

# Canonical column names we normalise every era/segment into.
CANON = [
    "date", "segment", "symbol", "series", "isin",
    "instrm_type", "strike", "opt_type",
    "open", "high", "low", "close", "last", "prevclose",
    "volume", "turnover", "trades", "oi", "oi_change",
]


class NotATradingDay(Exception):
    """Raised when NSE has no file for the date (weekend / holiday / not yet published)."""


@dataclass(frozen=True)
class Source:
    url: str
    era: str  # "udiff" or "legacy"


def _modern(segment: str, d: date) -> Source:
    seg = "cm" if segment == "cm" else "fo"
    tag = "CM" if segment == "cm" else "FO"
    return Source(
        f"https://nsearchives.nseindia.com/content/{seg}/"
        f"BhavCopy_NSE_{tag}_0_0_0_{d:%Y%m%d}_F_0000.csv.zip",
        "udiff",
    )


def _legacy(segment: str, d: date) -> Source:
    mmm = d.strftime("%b").upper()
    if segment == "cm":
        return Source(
            f"https://archives.nseindia.com/content/historical/EQUITIES/"
            f"{d.year}/{mmm}/cm{d.day:02d}{mmm}{d.year}bhav.csv.zip",
            "legacy",
        )
    return Source(
        f"https://archives.nseindia.com/content/historical/DERIVATIVES/"
        f"{d.year}/{mmm}/fo{d.day:02d}{mmm}{d.year}bhav.csv.zip",
        "legacy",
    )


def build_source(segment: str, d: date) -> Source:
    return _modern(segment, d) if d >= UDIFF_CUTOVER else _legacy(segment, d)


def download(src: Source, *, retries: int = 3, timeout: int = 45) -> bytes:
    """Fetch the zip bytes. Raises NotATradingDay on 404."""
    last = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(src.url, headers=HEADERS, timeout=timeout)
            if r.status_code == 404:
                raise NotATradingDay(src.url)
            r.raise_for_status()
            if r.content[:2] != b"PK":
                raise RuntimeError(f"Not a zip file (got {len(r.content)} bytes)")
            return r.content
        except NotATradingDay:
            raise
        except Exception as exc:  # noqa: BLE001 - retry on any transport error
            last = exc
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"Download failed after {retries} attempts: {last}") from last


def _read_csv(raw: bytes) -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(raw))
    name = z.namelist()[0]
    with z.open(name) as fh:
        return pd.read_csv(fh, dtype=str)


def _to_num(df: pd.DataFrame, cols: list[str]) -> None:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")


def parse(raw: bytes, segment: str, src: Source, d: date) -> pd.DataFrame:
    """Return a DataFrame in the canonical schema."""
    df = _read_csv(raw)

    if src.era == "udiff":
        mapping = {
            "TradDt": "date", "TckrSymb": "symbol", "SctySrs": "series", "ISIN": "isin",
            "OpnPric": "open", "HghPric": "high", "LwPric": "low", "ClsPric": "close",
            "LastPric": "last", "PrvsClsgPric": "prevclose", "TtlTradgVol": "volume",
            "TtlTrfVal": "turnover", "TtlNbOfTxsExctd": "trades",
            "OpnIntrst": "oi", "ChngInOpnIntrst": "oi_change",
            "FinInstrmTp": "instrm_type", "StrkPric": "strike", "OptnTp": "opt_type",
        }
        out = df.rename(columns=mapping)
    else:  # legacy
        mapping = {
            "SYMBOL": "symbol", "SERIES": "series", "ISIN": "isin",
            "OPEN": "open", "HIGH": "high", "LOW": "low", "CLOSE": "close",
            "LAST": "last", "PREVCLOSE": "prevclose", "TOTTRDQTY": "volume",
            "TOTTRDVAL": "turnover", "TOTALTRADES": "trades",
            "INSTRUMENT": "instrm_type", "STRIKE_PR": "strike", "OPTION_TYP": "opt_type",
        }
        out = df.rename(columns=mapping)
        out["date"] = d.isoformat()

    out["segment"] = segment.upper()
    if "date" not in out.columns:
        out["date"] = d.isoformat()

    _to_num(out, ["open", "high", "low", "close", "last", "prevclose",
                  "volume", "turnover", "trades", "oi", "oi_change", "strike"])

    for c in CANON:
        if c not in out.columns:
            out[c] = pd.NA

    out = out[CANON].dropna(subset=["symbol"])
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return out.reset_index(drop=True)


def fetch_day(d: date, segments=("cm", "fo")) -> dict[str, pd.DataFrame]:
    """Fetch and parse all requested segments for one date. Missing days are skipped."""
    frames: dict[str, pd.DataFrame] = {}
    for seg in segments:
        src = build_source(seg, d)
        try:
            raw = download(src)
        except NotATradingDay:
            continue
        frames[seg] = parse(raw, seg, src, d)
    if not frames:
        raise NotATradingDay(f"no data for {d.isoformat()}")
    return frames
