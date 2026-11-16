# Dashboard review — 2026-10-20

A UX review of `src/b3_pulse/dashboard/app.py` at commit `ff34794`. It was
done against the running app, not the code alone. Nothing was changed.
This file is the to-do list for the fixes.

**Audience assumed**: portfolio demo, i.e. a reviewer with no context and
about two minutes. That follows from the dashboard being the "productive
surface" of the Fase 3 brief.

**States checked**:

- a real result (PETR4.SA, data to 2026-09-04)
- an unknown ticker (`XXXX3.SA`)
- the API stopped
- dark mode
- a 375 px wide window

The stack was the MinIO container, `uv run b3-pulse-api` and
`uv run streamlit run src/b3_pulse/dashboard/app.py`. Quotes and predict
need MinIO running; metrics answer without it.

## Findings, by impact

### Trust

1. **The prediction has no uncertainty and no scale.** It shows "41.87,
   ↓ −5.30" next to an MAE of 1.678. The predicted move is about 3× the
   typical error, an 11% one-day drop, and nothing on screen says how far
   to trust it. Two decimals also suggest more precision than the model
   has.
   *Fix*: show an interval from the backtest residuals, round to the
   model's precision, and put "Typical error ±1.7 BRL" under the value.
   The known extrapolation limitation (see `architecture.md`, "Known
   limitation found while verifying 2c/2d live") belongs on the page as
   a caveat, not only in the docs.
2. **One champion model serves every ticker.** `/predict` always loads
   `models:/b3-pulse-baseline@champion` (trained on PETR4.SA), whatever
   ticker the sidebar holds. After ingesting another ticker, the page
   would show that ticker's "prediction" from the PETR4 model. Meanwhile
   `/model/metrics` filters runs by ticker, so the accuracy panel says
   "No trained model yet" while a prediction still renders.
   *Fix (API)*: return the training ticker with the prediction and refuse
   or warn on a mismatch. Or register one model per ticker.
3. **No staleness signal.** "As of 2026-09-04 00:00:00" was six weeks old
   on review day. The timestamp is also truncated at laptop width ("As of
   2026-09-04 00:…").
   *Fix*: format as a date and add a "Stale" badge past a few trading
   days.
4. **The model version is dropped.** `PredictionResponse.model_version`
   and the metrics' `run_id` reach the dashboard but aren't shown.
   *Fix*: one muted line under the result with the model, run id and data
   date.
5. **Metrics without units or a baseline.** MAE, RMSE and MAPE are
   printed with `st.write`, with no BRL and no naive baseline (tomorrow =
   today). There's nothing to judge 3.76% against.
   *Fix*: a small table with units, metric definitions in the column help,
   and a naive-baseline row. That row is also what the LSTM in Part 3 has
   to beat.

### States

6. **API down: raw exceptions.** The page shows three red boxes of
   `HTTPConnectionPool(...) Connection refused` text. In the narrow
   right column they wrap one word per line.
   *Fix*: one client module that maps errors to messages ("The model
   service is offline. Start it with `uv run b3-pulse-api`"), with the
   detail in an expander.
7. **Contradictory advice when the API is down.** "No data yet — click
   'Refresh data'" appears under the connection error, but that button
   calls the same unreachable API.
8. **Unknown ticker: wrong advice, three times.** `XXXX3.SA` produces
   three info boxes saying to ingest and train first. Nothing checks that
   the ticker exists.
   *Fix*: validate the ticker and show one message for the page.

### Visual

9. **The chart's y-axis starts at 0.** Prices of 30–50 are squeezed into
   the top half, which hides the movement the prediction is about.
   *Fix*: a domain fitted to the data, with the predicted point drawn as
   the next day on the chart.
10. **The result sits in a narrow side column.** The 3:1 column split
    makes the title wrap to two lines and "Baseline accuracy (backtest)"
    to three. The prediction, the actual output, is the smallest block.
    *Fix*: put the prediction first or wider, and use a shorter title.
11. **Smaller**:
    - stock theme, no `.streamlit/config.toml`
    - no one-sentence description of what the model does
    - the "Deploy" toolbar is visible (`client.toolbarMode = "minimal"`)
    - "Refresh data" doesn't say what it fetches or how long it takes

Dark mode and the 375 px layout work, apart from the zero-based axis
wasting space.

## Suggested split

- **Dashboard-only, can go now** (a small "2e"): 1 (rounding, typical
  error, limitation caveat), 3, 4, 6, 7, 8, 9, 10, 11.
- **With Part 3**: 2 and 5 change the API contract. Both fit naturally
  once a second model (the LSTM) has to be compared against the baseline
  and selected per ticker.
