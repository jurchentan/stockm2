# API Provider Evaluation

Initial provider decision:

- Implemented now: offline fixture provider and a Financial Modeling Prep adapter.
- Deferred: EODHD and SEC fallback adapters.

Why FMP first:

- Simple REST integration.
- Annual income statements, quote data, and company profile are available.
- Good enough to stand behind an interchangeable provider interface.

Current limitations of the FMP adapter in this repo:

- Historical PE is reconstructed from annual EPS and year-end close when enough data exists.
- Missing or sparse data raises normalization errors rather than silently guessing.
- The adapter is adequate for MVP usage, but fixture mode remains the most reliable path for deterministic tests.
