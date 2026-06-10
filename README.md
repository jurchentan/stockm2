# Stock M2

Stock M2 is a stock analysis app. It lets you enter stock tickers, run the Buffett-style model, and compare the current price with the model's projected prices.

It now also includes saved ticker presets, so you can keep watchlists like:

- Big Stocks 100
- S&P 500
- S&P 500 Tech
- S&P 500 Health Care
- S&P 500 Energy
- Your own custom saved lists

## Open The App Again

If the app is already set up on this computer, do this:

1. Open Terminal.
2. Go to this project folder:

```bash
cd /home/alex/projects/stockm2
```

3. Start the app:

```bash
.venv/bin/streamlit run src/stockm2/ui/app.py
```

4. Your browser should open automatically.
5. If it does not open, copy the local address shown in Terminal and paste it into your browser.
   It usually looks like `http://localhost:8501`

## What To Do In The App

1. Choose a data source on the left side.
2. Pick a preset from the `Preset` dropdown if you want a ready-made list.
3. Click `Load preset`.
4. Edit the tickers in the `Tickers` box if you want to customize the list.
5. If you want to save your own list, type a name into `Save as preset` and click `Save preset`.
6. Click `Run valuation`.

For each stock, the app shows:

- Current price
- Buy price
- Target price
- Sell price
- How far above or below the stock is versus the target price
- How far above or below the stock is versus the projected future price

## Saved Presets

Your custom presets are saved automatically in this file:

`/home/alex/projects/stockm2/.stockm2_ticker_presets.json`

This means your saved lists should still be there the next time you open the app.

## Saved Stock Records

The app can also save stock data into a permanent local database so loading big watchlists is faster next time.

That database file is:

`/home/alex/projects/stockm2/.stockm2_records.db`

In the app sidebar you can:

- turn saved stock records on or off
- clear all saved stock records if you want a full refresh

## First-Time Setup

Only use this part if the app does not start because the environment is missing.

1. Open Terminal.
2. Go to the project folder:

```bash
cd /home/alex/projects/stockm2
```

3. Install everything:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .[dev]
```

4. Then start the app:

```bash
.venv/bin/streamlit run src/stockm2/ui/app.py
```

## If Something Goes Wrong

- If Terminal says `No such file or directory`, make sure you are inside `/home/alex/projects/stockm2`
- If the browser page is blank, stop the app with `Ctrl+C` and start it again
- If the selected provider needs an API key, switch to `fixture` or `sec_yahoo`
- If a stock fails, the app will show an error for that ticker and continue with the others

## For Developers

Run tests:

```bash
.venv/bin/pytest
```

Run the CLI with fixture data:

```bash
.venv/bin/stockm2 buffett AAPL --fixture tests/fixtures/buffett_inputs.json
.venv/bin/stockm2 buffett --tickers AAPL,MSFT --format json
```
