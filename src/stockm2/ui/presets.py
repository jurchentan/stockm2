from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from stockm2.models.buffett import BuffettConfig


DEFAULT_PRESETS: dict[str, list[str]] = {
    "Big Stocks 100": [
        "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "AVGO", "META", "TSLA", "MU", "WMT", "AMD",
        "ASML", "INTC", "CSCO", "COST", "LRCX", "AMAT", "NFLX", "ARM", "PLTR", "KLAC", "TXN", "SNDK",
        "LIN", "MRVL", "PANW", "QCOM", "TMUS", "PEP", "ADI", "STX", "AMGN", "WDC", "APP", "CRWD",
        "GILD", "ISRG", "SHOP", "HON", "BKNG", "PDD", "SBUX", "VRTX", "CDNS", "MAR", "FTNT", "ADBE",
        "ADP", "MNST", "SNPS", "CSX", "CMCSA", "CEG", "MELI", "MDLZ", "DDOG", "INTU", "ABNB", "ORLY",
        "ROST", "MPWR", "NXPI", "CTAS", "AEP", "DASH", "WBD", "LITE", "REGN", "BKR", "PCAR", "FANG",
        "FAST", "EA", "ODFL", "XEL", "MCHP", "ADSK", "EXC", "FER", "IDXX", "CCEP", "KDP", "MSTR",
        "ALNY", "TTWO", "AXON", "PYPL", "PAYX", "TRI", "WDAY", "ROP", "GEHC", "DXCM", "CPRT", "KHC",
        "CTSH", "VRSK", "INSM", "ZS", "CHTR",
    ],
    "S&P 500": [
        "MMM", "AOS", "ABT", "ABBV", "ACN", "ADBE", "AMD", "AES", "AFL", "A", "APD", "ABNB", "AKAM", "ALB",
        "ARE", "ALGN", "ALLE", "LNT", "ALL", "GOOGL", "GOOG", "MO", "AMZN", "AMCR", "AEE", "AEP", "AXP",
        "AIG", "AMT", "AWK", "AMP", "AME", "AMGN", "APH", "ADI", "AON", "APA", "APO", "AAPL", "AMAT",
        "APP", "APTV", "ACGL", "ADM", "ARES", "ANET", "AJG", "AIZ", "T", "ATO", "ADSK", "ADP", "AZO",
        "AVB", "AVY", "AXON", "BKR", "BALL", "BAC", "BAX", "BDX", "BRK.B", "BBY", "TECH", "BIIB", "BLK",
        "BX", "XYZ", "BNY", "BA", "BKNG", "BSX", "BMY", "AVGO", "BR", "BRO", "BF.B", "BLDR", "BG",
        "BXP", "CHRW", "CDNS", "CPT", "CPB", "COF", "CAH", "CCL", "CARR", "CVNA", "CASY", "CAT", "CBOE",
        "CBRE", "CDW", "COR", "CNC", "CNP", "CF", "CRL", "SCHW", "CHTR", "CVX", "CMG", "CB", "CHD",
        "CIEN", "CI", "CINF", "CTAS", "CSCO", "C", "CFG", "CLX", "CME", "CMS", "KO", "CTSH", "COHR",
        "COIN", "CL", "CMCSA", "FIX", "CAG", "COP", "ED", "STZ", "CEG", "COO", "CPRT", "GLW", "CPAY",
        "CTVA", "CSGP", "COST", "CRH", "CRWD", "CCI", "CSX", "CMI", "CVS", "DHR", "DRI", "DDOG", "DVA",
        "DECK", "DE", "DELL", "DAL", "DVN", "DXCM", "FANG", "DLR", "DG", "DLTR", "D", "DPZ", "DASH",
        "DOV", "DOW", "DHI", "DTE", "DUK", "DD", "ETN", "EBAY", "SATS", "ECL", "EIX", "EW", "EA",
        "ELV", "EME", "EMR", "ETR", "EOG", "EQT", "EFX", "EQIX", "EQR", "ERIE", "ESS", "EL", "EG",
        "EVRG", "ES", "EXC", "EXE", "EXPE", "EXPD", "EXR", "XOM", "FFIV", "FDS", "FICO", "FAST", "FRT",
        "FDX", "FDXF", "FIS", "FITB", "FSLR", "FE", "FISV", "F", "FTNT", "FTV", "FOXA", "FOX", "BEN",
        "FCX", "GRMN", "IT", "GE", "GEHC", "GEV", "GEN", "GNRC", "GD", "GIS", "GM", "GPC", "GILD", "GPN",
        "GL", "GDDY", "GS", "HAL", "HIG", "HAS", "HCA", "DOC", "HSIC", "HSY", "HPE", "HLT", "HD", "HON",
        "HRL", "HST", "HWM", "HPQ", "HUBB", "HUM", "HBAN", "HII", "IBM", "IEX", "IDXX", "ITW", "INCY",
        "IR", "PODD", "INTC", "IBKR", "ICE", "IFF", "IP", "INTU", "ISRG", "IVZ", "INVH", "IQV", "IRM",
        "JBHT", "JBL", "JKHY", "J", "JNJ", "JCI", "JPM", "KVUE", "KDP", "KEY", "KEYS", "KMB", "KIM",
        "KMI", "KKR", "KLAC", "KHC", "KR", "LHX", "LH", "LRCX", "LVS", "LDOS", "LEN", "LII", "LLY", "LIN",
        "LYV", "LMT", "L", "LOW", "LULU", "LITE", "LYB", "MTB", "MPC", "MAR", "MRSH", "MLM", "MAS", "MA",
        "MKC", "MCD", "MCK", "MDT", "MRK", "META", "MET", "MTD", "MGM", "MCHP", "MU", "MSFT", "MAA",
        "MRNA", "TAP", "MDLZ", "MPWR", "MNST", "MCO", "MS", "MOS", "MSI", "MSCI", "NDAQ", "NTAP", "NFLX",
        "NEM", "NWSA", "NWS", "NEE", "NKE", "NI", "NDSN", "NSC", "NTRS", "NOC", "NCLH", "NRG", "NUE",
        "NVDA", "NVR", "NXPI", "ORLY", "OXY", "ODFL", "OMC", "ON", "OKE", "ORCL", "OTIS", "PCAR", "PKG",
        "PLTR", "PANW", "PSKY", "PH", "PAYX", "PYPL", "PNR", "PEP", "PFE", "PCG", "PM", "PSX", "PNW",
        "PNC", "POOL", "PPG", "PPL", "PFG", "PG", "PGR", "PLD", "PRU", "PEG", "PTC", "PSA", "PHM", "PWR",
        "QCOM", "DGX", "Q", "RL", "RJF", "RTX", "O", "REG", "REGN", "RF", "RSG", "RMD", "RVTY", "HOOD",
        "ROK", "ROL", "ROP", "ROST", "RCL", "SPGI", "CRM", "SNDK", "SBAC", "SLB", "STX", "SRE", "NOW",
        "SHW", "SPG", "SWKS", "SJM", "SW", "SNA", "SOLV", "SO", "LUV", "SWK", "SBUX", "STT", "STLD", "STE",
        "SYK", "SMCI", "SYF", "SNPS", "SYY", "TMUS", "TROW", "TTWO", "TPR", "TRGP", "TGT", "TEL", "TDY",
        "TER", "TSLA", "TXN", "TPL", "TXT", "TMO", "TJX", "TKO", "TTD", "TSCO", "TT", "TDG", "TRV", "TRMB",
        "TFC", "TYL", "TSN", "USB", "UBER", "UDR", "ULTA", "UNP", "UAL", "UPS", "URI", "UNH", "UHS", "VLO",
        "VEEV", "VTR", "VLTO", "VRSN", "VRSK", "VZ", "VRTX", "VRT", "VTRS", "VICI", "V", "VST", "VMC", "WRB",
        "GWW", "WAB", "WMT", "DIS", "WBD", "WM", "WAT", "WEC", "WFC", "WELL", "WST", "WDC", "WY", "WSM",
        "WMB", "WTW", "WDAY", "WYNN", "XEL", "XYL", "YUM", "ZBRA", "ZBH", "ZTS",
    ],
    "S&P 500 Tech": [
        "ACN", "ADBE", "AMD", "AKAM", "APH", "ADI", "AAPL", "AMAT", "APP", "ANET", "ADSK", "AVGO", "CDNS",
        "CDW", "CIEN", "CSCO", "CTSH", "COHR", "GLW", "CRWD", "DDOG", "DELL", "FFIV", "FICO", "FSLR", "FTNT",
        "IT", "GEN", "GDDY", "HPE", "HPQ", "IBM", "INTC", "INTU", "JBL", "KEYS", "KLAC", "LRCX", "LITE",
        "MCHP", "MU", "MSFT", "MPWR", "MSI", "NTAP", "NVDA", "NXPI", "ON", "ORCL", "PLTR", "PANW", "PTC",
        "QCOM", "Q", "ROP", "CRM", "SNDK", "STX", "NOW", "SWKS", "SMCI", "SNPS", "TEL", "TDY", "TER",
        "TXN", "TRMB", "TYL", "VRSN", "WDC", "WDAY", "ZBRA",
    ],
    "S&P 500 Health Care": [
        "ABT", "ABBV", "A", "ALGN", "AMGN", "BAX", "BDX", "TECH", "BIIB", "BSX", "BMY", "CAH", "COR", "CNC",
        "CRL", "CI", "COO", "CVS", "DHR", "DVA", "DXCM", "EW", "ELV", "GEHC", "GILD", "HCA", "HSIC", "HUM",
        "IDXX", "INCY", "PODD", "ISRG", "IQV", "JNJ", "LH", "LLY", "MCK", "MDT", "MRK", "MTD", "MRNA", "PFE",
        "DGX", "REGN", "RMD", "RVTY", "SOLV", "STE", "SYK", "TMO", "UNH", "UHS", "VEEV", "VRTX", "VTRS", "WAT",
        "WST", "ZBH", "ZTS",
    ],
    "S&P 500 Energy": [
        "APA", "BKR", "CVX", "COP", "DVN", "FANG", "EOG", "EQT", "EXE", "XOM", "HAL", "KMI", "MPC", "OXY",
        "OKE", "PSX", "SLB", "TRGP", "TPL", "VLO", "WMB",
    ],
}


def _default_presets_path() -> Path:
    configured_path = os.getenv("STOCKM2_PRESETS_PATH")
    if configured_path:
        return Path(configured_path)
    return Path(".stockm2_ticker_presets.json")


def normalize_tickers(tickers: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        upper = ticker.strip().upper()
        if not upper or upper in seen:
            continue
        seen.add(upper)
        normalized.append(upper)
    return normalized


def load_custom_presets(path: Path | None = None) -> dict[str, list[str]]:
    preset_path = path or _default_presets_path()
    if not preset_path.exists():
        return {}
    payload = json.loads(preset_path.read_text())
    if not isinstance(payload, dict):
        return {}
    custom_presets: dict[str, list[str]] = {}
    for name, tickers in payload.items():
        if not isinstance(name, str) or not isinstance(tickers, list):
            continue
        custom_presets[name] = normalize_tickers([str(ticker) for ticker in tickers])
    return custom_presets


def save_custom_presets(custom_presets: dict[str, list[str]], path: Path | None = None) -> Path:
    preset_path = path or _default_presets_path()
    payload = {name: normalize_tickers(tickers) for name, tickers in sorted(custom_presets.items())}
    preset_path.write_text(json.dumps(payload, indent=2) + "\n")
    return preset_path


def load_all_presets(path: Path | None = None) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    custom_presets = load_custom_presets(path)
    all_presets = dict(DEFAULT_PRESETS)
    all_presets.update(custom_presets)
    return all_presets, custom_presets


def _default_assumption_presets_path() -> Path:
    configured_path = os.getenv("STOCKM2_ASSUMPTION_PRESETS_PATH")
    if configured_path:
        return Path(configured_path)
    return Path(".stockm2_assumption_presets.json")


def serialize_config(config: BuffettConfig) -> dict[str, object]:
    return asdict(config)


def deserialize_config(payload: dict[str, object]) -> BuffettConfig:
    allowed_fields = BuffettConfig.__dataclass_fields__
    normalized_payload = {name: value for name, value in payload.items() if name in allowed_fields}
    return BuffettConfig(**normalized_payload)


def load_assumption_presets(path: Path | None = None) -> dict[str, BuffettConfig]:
    preset_path = path or _default_assumption_presets_path()
    if not preset_path.exists():
        return {}
    payload = json.loads(preset_path.read_text())
    if not isinstance(payload, dict):
        return {}
    presets: dict[str, BuffettConfig] = {}
    for name, config_payload in payload.items():
        if not isinstance(name, str) or not isinstance(config_payload, dict):
            continue
        presets[name] = deserialize_config(config_payload)
    return presets


def save_assumption_presets(presets: dict[str, BuffettConfig], path: Path | None = None) -> Path:
    preset_path = path or _default_assumption_presets_path()
    payload = {name: serialize_config(config) for name, config in sorted(presets.items())}
    preset_path.write_text(json.dumps(payload, indent=2) + "\n")
    return preset_path
