# Legacy Buffett Model

The legacy Buffett pipeline lives in `model/` and executes on import:

- `input.py` loads tickers, fetches QuickFS metrics, and creates `Stock` objects.
- `eps.py` filters stocks with more than two non-positive EPS growth years.
- `buysell.py` ranks accepted stocks by current price versus buy price.

Core formulas from `model/obj/Stock.py`:

- Weighted EPS growth uses weights `[0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3, 1.5]`.
- EPS growth is clipped to `[-0.5, 0.5]` before averaging.
- Average PE is the mean of the ten historical PE values.
- Dampener starts at `0.8`, subtracts `0.1` for each negative weighted EPS growth value, then adds `0.1` back if any reduction occurred.
- Projected EPS uses ten rounds of compound growth from the latest EPS.
- Projected future price is `projected_eps * target_pe`.
- Discounted target price uses `18%` over ten years.
- Buy price applies a `25%` margin of safety.
- Sell price uses `15%` over ten years, but the legacy object does not return it as part of the primary output.

Important quirks preserved in tests and the new model's legacy defaults:

- Negative-year counting happens after weighting.
- The dampener checks `growth < 0`, while the filter checks `growth <= 0`.
- Buy-price gap is `(current_price - buy_price) / buy_price` and can divide by zero.
- The object stores `EPS_2023` even though the model is conceptually using latest EPS.
