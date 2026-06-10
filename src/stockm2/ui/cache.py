from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path

from stockm2.models.buffett import BuffettInput, DataSource


def _database_path() -> Path:
    configured_path = os.getenv("STOCKM2_DB_PATH")
    if configured_path:
        return Path(configured_path)
    return Path(".stockm2_records.db")


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path())
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_inputs (
            provider_name TEXT NOT NULL,
            provider_scope TEXT NOT NULL,
            ticker TEXT NOT NULL,
            years INTEGER NOT NULL,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (provider_name, provider_scope, ticker, years)
        )
        """
    )
    connection.commit()
    return connection


def serialize_buffett_input(stock_input: BuffettInput) -> dict[str, object]:
    return asdict(stock_input)


def deserialize_buffett_input(payload: dict[str, object]) -> BuffettInput:
    sources_payload = payload.get("sources", [])
    sources = [DataSource(**source) for source in sources_payload]
    return BuffettInput(
        ticker=str(payload["ticker"]),
        company_name=str(payload["company_name"]),
        latest_eps=float(payload["latest_eps"]),
        eps_growth_history=[float(value) for value in payload.get("eps_growth_history", [])],
        pe_history=[float(value) for value in payload.get("pe_history", [])],
        current_price=float(payload["current_price"]),
        fiscal_years=[str(value) for value in payload.get("fiscal_years", [])],
        sources=sources,
    )


def load_cached_input(provider_name: str, provider_scope: str, ticker: str, years: int) -> BuffettInput | None:
    connection = _connect()
    try:
        row = connection.execute(
            """
            SELECT payload
            FROM stock_inputs
            WHERE provider_name = ? AND provider_scope = ? AND ticker = ? AND years = ?
            """,
            (provider_name, provider_scope, ticker.upper(), years),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    payload = json.loads(row[0])
    if not isinstance(payload, dict):
        return None
    return deserialize_buffett_input(payload)


def save_cached_input(provider_name: str, provider_scope: str, ticker: str, years: int, stock_input: BuffettInput) -> Path:
    connection = _connect()
    try:
        connection.execute(
            """
            INSERT INTO stock_inputs (provider_name, provider_scope, ticker, years, payload, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(provider_name, provider_scope, ticker, years)
            DO UPDATE SET payload = excluded.payload, updated_at = CURRENT_TIMESTAMP
            """,
            (
                provider_name,
                provider_scope,
                ticker.upper(),
                years,
                json.dumps(serialize_buffett_input(stock_input)),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    return _database_path()


def clear_input_cache() -> None:
    connection = _connect()
    try:
        connection.execute("DELETE FROM stock_inputs")
        connection.commit()
    finally:
        connection.close()
