# Legacy Data Sources

The legacy code uses the deprecated `quickfs` package and requests these metrics:

- `eps_diluted_growth`
- `price_to_earnings`
- `eps_diluted`
- `period_end_price`

Known problems:

- Import-time network calls block testing and reuse.
- The API key is printed to stdout in `model/input.py`.
- Period-end price is used in place of a live market price.
- Metadata such as company name is only partially wired.

The modernized code routes all provider access through `stockm2.data.providers` and supports:

- Offline fixture-based analysis for tests and local demos.
- A live Financial Modeling Prep adapter when an API key is configured.
