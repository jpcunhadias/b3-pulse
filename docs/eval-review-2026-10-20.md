# Evaluation review — 2026-10-20

A review of how the baseline model (`src/b3_pulse/models/baseline/train.py`)
is evaluated and served, at commit `ff34794`. The local clone is behind
GitHub, but the commit it lacks only adds the licence. Nothing in the
project was changed, retrained or re-registered. The numbers were
recomputed with a scratch script that imports the project's own loader and
split, plus the registered `champion` model, read-only. The data was read
from MinIO with `docker compose -f infra/docker-compose.yml up -d`, and the
container was stopped afterwards. Companion to
[`dashboard-review-2026-10-20.md`](dashboard-review-2026-10-20.md).

How each finding was established: **checked** means recomputed; **read**
means taken from the code.

## Verdict

| Area | Verdict |
|---|---|
| Leakage | Sound |
| Baseline | **Broken**: no naive baseline, and the model loses to persistence by 3× |
| Metric | Weak: a single aggregate over a regime change |
| Spread | Weak: one split, no interval |
| Calibration | n/a: point forecasts only |
| Train/serve | **Broken**: outside the training price range, one model for every ticker, "champion" means newest |
| Traceability | Weak: the logged run can't be tied to today's data without reconstructing it |

## Findings

### Overstates the number

1. **The model is three times worse than "tomorrow = today"** (checked).
   On the served model's own held-out days (2025-09-26 → 2026-09-03,
   n = 234):

   | Predictor | MAE (BRL) |
   |---|---|
   | Gradient boosting (`champion`, run `e110c1d9`) | **1.677** (logged: 1.678) |
   | Persistence: tomorrow's close = today's close | **0.536** |

   The project calls this model "a real baseline to beat"
   (`docs/architecture.md:93`), but it doesn't beat the trivial
   forecaster. Nowhere is MAE compared against persistence.
   (`train.py:51-58` computes the model's metrics only.)

2. **It gets worse the further it goes** (checked). Here are MAE by
   quarter on days after the model's training cutoff (2025-09-25):

   | Quarter ending | Model | Persistence |
   |---|---|---|
   | 2026-03-31 | 1.132 | 0.451 |
   | 2026-09-03 | 2.436 | 0.670 |

   On the 66 test days whose target is above the highest training close
   (42.90 BRL), model MAE is 4.77 against 0.81 for persistence. The model
   predicts too low on average (mean signed error −0.76 BRL on the
   longer window). The single aggregate MAE hides this trend.

3. **One split and no spread** (read). `chronological_split`
   (`train.py:37-42`) holds out the last 20% once. That's the right
   direction for a time series, but it gives one draw. Use a
   rolling-origin backtest (several cutoffs), or at least a
   block-bootstrap interval. The gap in finding 1 is large enough that no
   interval changes the conclusion. Any future comparison with the LSTM
   needs one.

### Misleads in use

4. **Trees can't extrapolate, and the model is fed price levels**
   (read and checked). `FEATURE_COLUMNS` (`train.py:20`) are price levels
   (`closing_price`, `ma_5`, `ma_10`) and the target is a level
   (`build.py:35`). Gradient-boosted trees can't predict outside the
   target range they were trained on. Once PETR4 rose above about 43 BRL,
   every prediction was capped near the old maximum. That is the 11%
   under-prediction recorded in `docs/architecture.md:122-129`, and the
   −5.30 shown on the dashboard. *Fix*: predict the next-day return (or
   the change), and add the last close back afterwards. Make
   persistence the reference.

5. **One model serves every ticker** (read). `MODEL_URI` is fixed at
   `models:/b3-pulse-baseline@champion` (`service.py:15`, `:68`). The
   model was trained on PETR4.SA only, but `/predict` uses it for any
   ticker. `/model/metrics` filters runs by ticker (`service.py:90`), so
   the two endpoints disagree about which model exists. *Fix*: one
   registered model or alias per ticker, or refuse other tickers.

6. **"champion" means newest, not best** (read). Every training run moves
   the alias (`train.py:80`), whatever its metrics. A worse retrain
   silently replaces the served model. *Fix*: move the alias only when
   the new run beats the current champion (and persistence) on the same
   held-out window.

### Presentation and traceability

7. **The logged metric can't be reproduced from today's data** (checked).
   Run `e110c1d9` logged `n_train=933, n_test=234` (`train.py:73-74`): a
   dataset from 2022-01-04 to 2026-09-03. The warehouse now holds 2,156
   rows from 2018 (`config.py:8`, `start_date = "2018-01-01"`). Running
   `chronological_split` on today's data gives a different test window
   (2024-12-10 → 2026-09-03). That window overlaps the served model's
   training rows and makes it look about 40% better (MAE 1.04). The
   original split had to be rebuilt from the run's row counts and start
   time. *Fix*: log the data's date range (first/last `trade_date`) and
   the split cutoff with each run.

8. **The documented training range is wrong** (checked).
   `docs/architecture.md:124` says the model was "trained on ~2022–2024
   data". The served model was trained on 2022-01-04 → 2025-09-25.

9. **MAPE is fine here; keep it in percent** (read). Prices are far from
   zero, so MAPE is stable. It is logged as a fraction (`0.0376`); the
   dashboard shows it as a percentage, which is correct.

Leakage checks passed (read):

- The split is chronological.
- The rolling features look back only (`build.py:21-33`).
- The label is the one forward column (`build.py:35`).
- Nothing is fitted before the split.
- No hyperparameters were tuned on the test set; they are fixed in
  `train.py:51`.

## Honest claim, as things stand

> A gradient-boosting baseline predicting PETR4's next-day close scores
> MAE 1.68 BRL on the last 234 trading days to 2026-09-03 (one
> chronological split). Predicting today's close scores 0.54 BRL on the
> same days. The model under-predicts once prices leave its training
> range.

Don't put "MAE 1.68" anywhere without the persistence figure next to it.

## Fixes, smallest first

1. Add persistence (and `ma_5`) to `train_and_evaluate` and log them in
   the same run. *Training code only.*
2. Log the data's date range and the split cutoff. *Training code only.*
3. Correct `docs/architecture.md:124` and add the persistence comparison
   to the known limitation. *Docs.*
4. Predict returns instead of levels, then retrain and compare against
   persistence. *Needs retraining; changes the served model.*
5. Move `champion` only on improvement. Add per-ticker models or a
   ticker check. *Changes the API contract; pairs with dashboard-review
   findings 2 and 5.*
6. Use a rolling-origin backtest with an interval before comparing the
   LSTM in Part 3. *Part 3.*
