from __future__ import annotations

import json

from stockm2.cli import main


def test_cli_json_output(capsys) -> None:
    exit_code = main(["buffett", "AAPL", "--fixture", "tests/fixtures/buffett_inputs.json", "--format", "json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload[0]["ticker"] == "AAPL"
    assert "buy_price" in payload[0]


def test_cli_table_output_multiple_tickers(capsys) -> None:
    exit_code = main([
        "buffett",
        "--tickers",
        "AAPL,MSFT",
        "--fixture",
        "tests/fixtures/buffett_inputs.json",
        "--format",
        "table",
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "ticker\taccepted" in captured.out
    assert "AAPL" in captured.out
    assert "MSFT" in captured.out
