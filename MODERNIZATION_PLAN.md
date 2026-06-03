# Stock M2 Modernization Plan

## Purpose

Stock M2 is a value-investing research tool. The first modernization target is the Warren Buffett / Buffettology model in `model/`, which estimates a fair buy price from historical EPS growth, projected future EPS, average PE, a target return, and a margin of safety.

This document is the implementation plan only. It does not change the legacy model behavior.

## Current Repo Snapshot

The repo currently contains three strategy areas:

- `model/`: primary Buffettology-style EPS growth and PE valuation model.
- `greenblatt_model/`: Joel Greenblatt magic formula experiment using earnings yield and ROIC.
- `graham_model/`: Ben Graham net asset value experiment.
- `backtesting/`: placeholder only.
- `test/`: saved QuickFS sample outputs and exploratory notes, not automated tests.
- `R1 EXCEL 26Jun2024/`: CSV exports that appear to be external research data.
- `quickfs_api_doc.yaml`: archived QuickFS API documentation.

The Buffett model currently runs as import-time scripts:

- `model/input.py` loads tickers, calls QuickFS, builds `Stock` objects, and prints data.
- `model/eps.py` imports `all_stocks` from `input.py`, filters stocks by EPS growth quality, ranks them, and prints results.
- `model/buysell.py` imports `good_stocks` from `eps.py`, ranks by current price versus buy price, and prints each evaluation.
- `model/obj/Stock.py` contains most of the actual Buffett model math.

## Legacy Buffett Model Behavior

The current Buffett model uses these inputs per stock:

- `ticker`
- `stock_name`
- latest diluted EPS, currently named `EPS_2023`
- 10 annual diluted EPS growth values from QuickFS metric `eps_diluted_growth`
- 10 annual PE values from QuickFS metric `price_to_earnings`
- current or period-end price from QuickFS metric `period_end_price`

The current calculations are:

- Applies weighted EPS growth by default with weights `[0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3, 1.5]`.
- Clips EPS growth values to `+/- 50%` before averaging.
- Rejects stocks with more than two non-positive EPS growth years.
- Calculates average PE from the 10-year PE series.
- Starts with a max dampener of `0.8`, subtracts `0.1` for each negative EPS growth year, then adds back `0.1` if any reduction occurred.
- Projects future EPS for 10 years using `latest_eps * (1 + average_eps_growth * dampener) ^ 10`.
- Projects future price as `projected_eps * target_pe`.
- Discounts the projected price back 10 years at a target return of `18%`.
- Applies a `25%` margin of safety to produce the buy price.
- Computes percentage above or below the buy price from the current price.

Important legacy limitations:

- QuickFS dependency is deprecated and blocks normal usage.
- Scripts execute work at import time, which prevents clean testing and reuse.
- API keys are printed to stdout in some paths.
- Data provider logic, data normalization, model math, filtering, ranking, and terminal output are mixed together.
- The model uses a hard-coded 2023 naming assumption and a fixed 10-year projection window.
- It returns only `buy_price`; target price, sell price, assumptions, and intermediate values are not first-class output.
- PE, EPS, and current price validation is minimal.
- There are no automated unit tests, integration tests, fixtures, CLI contract tests, or backtests.
- Generated `__pycache__/` files are present in the repo.

## Modernization Goals

The immediate goal is not to make the model more complicated. The goal is to make it usable, documented, testable, and replaceable.

Primary goals:

- Preserve the legacy Buffett model as a documented reference.
- Replace QuickFS with a sustainable data layer.
- Extract the Buffett model into pure, tested functions or classes.
- Make model assumptions explicit and configurable.
- Add a reliable CLI first; add UI only after the model and data pipeline are stable.
- Add black-box tests using fixed fixture data before changing model math.
- Keep Greenblatt and Graham code archived or documented, but out of scope for the first modernization pass.

Non-goals for the first pass:

- Do not optimize the investing strategy before the legacy behavior is captured.
- Do not build a full web app before data and model reliability are solved.
- Do not merge Buffett, Graham, and Greenblatt into one framework yet.
- Do not introduce portfolio management, brokerage integration, or trading automation.

## Phase 1: Archive And Document Legacy Code

Actions:

- Create an `archive/legacy_quickfs/` area for old script-oriented QuickFS code after the replacement architecture is ready.
- Preserve the exact legacy Buffett scripts and QuickFS docs so old behavior remains inspectable.
- Move or remove committed `__pycache__/` files and update `.gitignore` if needed.
- Add a legacy behavior document for the Buffett pipeline covering `input.py -> eps.py -> buysell.py`.
- Document all legacy model constants and formulas.
- Record known input assumptions, especially the 10-year EPS growth window, average PE assumption, dampener, target return, sell return, and margin of safety.
- Mark Greenblatt and Graham folders as legacy experiments for now, with short README files explaining that they are out of scope for the current pass.

Deliverables:

- `docs/legacy-buffett-model.md`
- `docs/legacy-data-sources.md`
- `archive/legacy_quickfs/` or an equivalent archive path
- Cleaned generated files and `.gitignore` updates

## Phase 2: Add Baseline Tests Before Refactoring

Actions:

- Build deterministic fixture data from `test/quickfs_api_template.txt` or smaller hand-written examples.
- Add black-box tests that assert current Buffett outputs for known inputs.
- Test the formula behavior directly: EPS weighting, EPS clipping, negative-growth filtering, dampener calculation, future EPS projection, buy price, and above/below percentage.
- Add regression tests for edge cases: zero price, negative EPS, missing PE, insufficient EPS history, negative projected EPS, and non-numeric API data.
- Choose a modern Python test runner, likely `pytest`.

Deliverables:

- `tests/test_buffett_model_legacy_behavior.py`
- `tests/fixtures/` with small normalized fixture files
- A documented command such as `pytest`

## Phase 3: Extract The Buffett Model Core

Actions:

- Create a new source layout, likely `src/stockm2/`.
- Extract pure Buffett model code into a module such as `stockm2/models/buffett.py`.
- Replace the mutable script-style `Stock` object with explicit input and output objects.
- Return structured valuation output with all relevant intermediate values.
- Keep defaults matching legacy constants until tests prove behavior is preserved.
- Make assumptions configurable through a `BuffettConfig` object.

Proposed model objects:

- `BuffettInput`: ticker, company name, latest EPS, EPS growth history, PE history, current price, fiscal years.
- `BuffettConfig`: forecast years, target return, sell return, margin of safety, max EPS growth, dampener settings, weighting settings.
- `BuffettValuation`: average EPS growth, adjusted EPS growth, average PE, projected EPS, projected future price, target price, buy price, optional sell price, current-price gap, rejection reasons.

Deliverables:

- Pure model module with no API calls and no printing.
- Tests that compare new output to legacy fixture output.
- Type hints for all model inputs and outputs.

## Phase 4: Replace QuickFS With A Data Provider Layer

The model needs annual historical values for at least:

- Diluted EPS or enough income statement data to compute it.
- Annual EPS growth or enough EPS history to compute it internally.
- Historical annual PE or enough historical price and EPS data to compute it.
- Current price.
- Company name and ticker metadata.

Provider candidates to evaluate:

- Financial Modeling Prep: strong candidate because it offers historical financial statements and ratios through API products.
- EODHD: strong candidate because it advertises fundamentals, financial highlights, PE ratio, EPS, and broad exchange coverage.
- Finnhub: possible candidate for basic financials, EPS, PE, and market data; needs validation for annual historical depth and licensing.
- Alpha Vantage: already partially explored in the repo, but likely weaker for consistent 10-year annual fundamentals and batch throughput.
- SEC EDGAR Companyfacts: reliable free source for U.S. reported fundamentals, but it does not directly provide clean PE/current price and requires substantial normalization.
- Hybrid SEC plus market-data provider: robust long-term option if paid APIs are not desired, but slower to implement.

Recommended evaluation criteria:

- Annual EPS history depth for U.S. equities.
- Historical PE availability or ability to reconstruct it from price and EPS.
- Batch request support for hundreds of tickers.
- Data licensing for personal research versus possible app distribution.
- Rate limits, pricing, and reliability.
- Python SDK quality or simple REST support.
- Symbol coverage for Russell 1000 / 2000 style universes.
- Restatement handling and fiscal-year consistency.

Initial recommendation:

- Start with Financial Modeling Prep or EODHD if a paid API is acceptable.
- Use SEC Companyfacts as a future fallback or verification source, not as the first replacement, because reconstructing clean historical EPS and PE will delay model modernization.
- Keep the data provider behind an interface so the provider can be swapped later.

Proposed provider interface:

```python
class FundamentalsProvider:
    def get_annual_buffett_inputs(self, ticker: str, years: int) -> BuffettInput:
        ...
```

Deliverables:

- `stockm2/data/providers/base.py`
- One implemented provider adapter.
- Provider fixture tests with recorded sample responses.
- Clear `.env.example` entries for API keys without printing secrets.

## Phase 5: Add A Modern CLI

Actions:

- Add a CLI entry point such as `stockm2 buffett AAPL`.
- Support single ticker and ticker-list input.
- Support JSON and table output.
- Add flags for forecast years, target return, margin of safety, provider, and offline fixture mode.
- Ensure the CLI never prints API keys.

Example commands:

```bash
stockm2 buffett AAPL
stockm2 buffett --tickers AAPL,MSFT,KO --format table
stockm2 buffett --input tickers.txt --format json
stockm2 buffett --fixture tests/fixtures/aapl_buffett.json
```

Deliverables:

- CLI module and package entry point.
- CLI black-box tests.
- README usage examples.

## Phase 6: Add Backtesting

Actions:

- Define what a signal means before coding: buy when current price is below model buy price, sell when above sell/target threshold, or hold otherwise.
- Use point-in-time fundamentals where possible to avoid look-ahead bias.
- Create a backtest that compares model signals against future returns over 1, 3, 5, and 10 year windows.
- Track hit rate, annualized return, drawdown, and benchmark comparison.
- Separate strategy validation from valuation output.

Deliverables:

- `stockm2/backtesting/` module.
- Backtest fixtures or cached provider data.
- Documentation on backtest assumptions and known biases.

## Phase 7: Add UI Or API After The Core Is Stable

The first UI should be small and boring: show assumptions, inputs, valuation output, and rejection reasons clearly.

Possible paths:

- Streamlit for quickest local research UI.
- FastAPI plus a small frontend if a reusable API is desired.
- Static report generation if the main workflow is batch screening.

Recommended first UI:

- Start with a CLI and JSON output.
- Add generated Markdown or HTML valuation reports.
- Only then build an interactive UI.

## Proposed Target Structure

```text
stockm2/
  MODERNIZATION_PLAN.md
  README.md
  pyproject.toml
  .env.example
  docs/
    legacy-buffett-model.md
    legacy-data-sources.md
    api-provider-evaluation.md
  archive/
    legacy_quickfs/
  src/
    stockm2/
      models/
        buffett.py
      data/
        providers/
          base.py
          fmp.py
          eodhd.py
      cli.py
      backtesting/
  tests/
    fixtures/
    test_buffett_model_legacy_behavior.py
    test_buffett_cli.py
```

## Recommended First Work Items

1. Add `docs/legacy-buffett-model.md` with exact formulas and the current pipeline.
2. Add `tests/` with black-box tests for `model/obj/Stock.py` using fixed data.
3. Add `pyproject.toml` and move dependency management out of the old pinned `requirements.txt` workflow.
4. Extract the Buffett formula into `src/stockm2/models/buffett.py` while preserving legacy outputs.
5. Evaluate Financial Modeling Prep and EODHD with one or two tickers before committing to a provider.
6. Implement one provider adapter and normalize provider output into `BuffettInput`.
7. Add a CLI around the normalized provider plus pure model.
8. Archive QuickFS scripts once the new path can reproduce at least one fixture valuation.

## Open Decisions

- Should the first replacement provider be paid API first, or free/open-data first?
- Should the model use historical fiscal-year-end prices for historical PE, average annual close, or provider-reported historical PE?
- Should EPS growth be computed internally from EPS history instead of trusting provider-reported EPS growth?
- Should the weighting scheme remain default behavior or become an optional strategy setting?
- What should count as a consumer monopoly / moat filter in software: manual tag, external qualitative checklist, or no automated filter for now?
- Should non-Buffett models be archived immediately or left untouched until the Buffett rewrite lands?

## Success Criteria For The First Modernization Milestone

- The legacy Buffett model is documented well enough that the formulas can be reimplemented from the docs.
- The repo has automated tests for the core valuation behavior.
- Running model code does not require QuickFS.
- Model math can run offline from fixture data.
- A single ticker can be valued through a documented CLI command.
- API keys are not printed or committed.
- Greenblatt and Graham experiments remain preserved but do not block the Buffett model cleanup.
