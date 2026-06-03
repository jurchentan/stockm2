# Backtesting Notes

The MVP backtesting module is intentionally simple and deterministic.

Signal definition:

- `buy` when `current_price <= buy_price`
- `sell` when `current_price >= target_price`
- `hold` otherwise

Known biases:

- Fixture-driven backtests do not model point-in-time data revisions.
- Future returns are only as good as the provided fixture outcomes.
- The module is suitable for regression checks and scenario experiments, not production-grade research.
