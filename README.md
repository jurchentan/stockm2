# Stock M2

Stock M2 is a modernized Buffett-style stock valuation toolkit with:

- A pure, testable Buffett model in `src/stockm2/models/buffett.py`
- Provider interfaces for offline fixtures and live APIs
- A CLI for repeatable scripting
- A Streamlit UI for local interactive analysis
- A small backtesting module for deterministic signal experiments

## Quick Start

Install in editable mode:

```bash
pip install -e .[dev]
```

Run tests:

```bash
pytest
```

Run the CLI with fixture data:

```bash
stockm2 buffett AAPL --fixture tests/fixtures/buffett_inputs.json
stockm2 buffett --tickers AAPL,MSFT --format json
```

Run the Streamlit UI:

```bash
streamlit run src/stockm2/ui/app.py
```

## Project Structure

- `src/stockm2/models/`: Buffett valuation logic
- `src/stockm2/data/providers/`: provider interface plus fixture and FMP adapters
- `src/stockm2/ui/`: Streamlit MVP UI
- `src/stockm2/backtesting/`: simple signal and backtest helpers
- `tests/`: fixture-driven unit and CLI tests
- `docs/`: legacy behavior, data source notes, provider evaluation, and backtesting notes
- `model/`: legacy QuickFS-era reference code
- `greenblatt_model/`, `graham_model/`: archived experiments

## Legacy Reference

The legacy Buffett pipeline remains documented for reference:

- `docs/legacy-buffett-model.md`
- `docs/legacy-data-sources.md`
- `MODERNIZATION_PLAN.md`
