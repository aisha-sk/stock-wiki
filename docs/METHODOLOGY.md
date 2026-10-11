# Methodology and limitations

How every figure in StockSense is produced, so a sceptical reader can check it. Numbers below are
from the artifacts generated `2026-10-11T00:10:32Z` (`data/artifacts/model.json`). Code paths are
given so each claim can be traced.

Sentiment and the forecast are separate. The forecast does not use the sentiment shown on the
page, apart from one lagged news feature described below. Neither is financial advice.

## 1. Data sources

| Data | Source | What it misses |
|---|---|---|
| Daily prices (OHLCV) | Yahoo Finance via `yfinance`, 2 years, NYSE sessions only (`ml/ingest/prices.py`) | Intraday moves. Yahoo data is unofficial and can be revised. |
| News headlines | Finnhub company news when `FINNHUB_API_KEY` is set, else Yahoo Finance, else Google News RSS (`ml/ingest/news.py`). Option-chain and quote pages are filtered out. | Article bodies (titles only). Paywalled and non-English coverage. |
| Analyst ratings | Finnhub recommendation trends, or Yahoo Finance recommendations without a key (`ml/ingest/analysts.py`) | Price targets and the reasoning behind a rating. Counts are monthly. |
| Reddit posts | **Not collected.** The code in `ml/ingest/reddit.py` is switched off. See below. | Everything. |

**There is no Reddit data.** Reddit's Responsible Builder Policy requires explicit approval
before any access to Reddit data, including the public search feeds. The first version of the
pipeline requested those feeds without approval; every request on 2026-10-10 was refused with
HTTP 429, so no Reddit data was ever collected or published. The fetch is now switched off
(`REDDIT_ENABLED` in `ml/pipeline.py`) until access is approved. The page compares analysts and
news only.

## 2. Sentiment

- **Text (news, Reddit):** each title is scored with FinBERT (`ProsusAI/finbert`) as
  `score = round((P(positive) - P(negative)) * 100)`, from -100 to +100
  (`ml/sentiment/finbert.py`). A source's score is the mean of its titles from the last
  **7 days**, rounded to an integer (`ml/sentiment/aggregate.py`). `previous_score` is the
  same mean for the 7 days before that.
- **Analysts:** `score = round(100 * (2*strong_buy + buy - sell - 2*strong_sell) / (2 * total))`
  from the latest month of counts. This is a **ratings consensus, not text sentiment**, and the
  page labels it so. It is on the same -100 to +100 scale so it can sit beside the others.
- **Labels:** at least +20 is bullish, at most -20 is bearish, anything between is neutral
  (`ml/sentiment/labels.py`).
- **Gap:** the highest score minus the lowest among the sources present. It is `null` with fewer
  than two sources. The summary sentence uses each source's own label, and says the groups are
  close together under 20 points (`ml/sentiment/gap.py`).

Current values:

| Stock | Analysts | News | Reddit | Gap |
|---|---|---|---|---|
| TSLA | +19 neutral (44 analysts) | +22 bullish (51 articles) | missing | 3 |
| NVDA | +55 bullish (62 analysts) | +15 neutral (69 articles) | missing | 40 |
| AAPL | +25 bullish (44 analysts) | +8 neutral (52 articles) | missing | 17 |

## 3. Forecast

**Task:** will the absolute move over the next 5 sessions be larger than the typical move? The
model does not say which way. Earlier versions (1 to 7) predicted up or down instead; they are
kept in the registry with `task: "direction"`.

- **Target:** for day *t*, the return from the close of *t* to the close of *t*+5. "Large" means
  its absolute value is above the **typical move**: the median absolute 5-session return over
  that fold's training rows only. Test rows use that frozen number and never help compute it
  (`ml/train.py`, leakage test in `ml/tests/test_train.py`). A median split keeps "large" near
  half of all sessions. The live forecast uses the median of every labelled session.
- **Features** (each uses data up to the close of day *t* only, `ml/features.py`): 1, 5 and
  10-day returns, 10 and 20-day volatility, 14-day RSI, volume against its 20-day mean, the gap
  to the 20-day moving average, and `news_lag1`, the mean FinBERT score of headlines in the
  7 days ending the session before *t* (Google News RSS history). The sentiment shown on the
  page is not otherwise a feature.
- **Model:** XGBoost, `n_estimators=200`, `max_depth=3`, `learning_rate=0.05`, `subsample=0.8`,
  fixed in advance, no search. The three stocks are pooled.
- **Walk-forward validation:** an expanding training window starting at 252 sessions, then test
  blocks of 21 sessions, moving 21 sessions at a time. Folds are cut by date, so no stock's
  future leaks through another's. The 5 sessions before each test block are **purged** from
  training, because their targets overlap the test period. No random splits.
- **Baselines**, scored on the same test rows: `always_quiet` (always says a typical move) and
  `previous_move` (says large only when the last 5 sessions were already a large move).

## 4. Results as measured

Test period 2025-11-11 to 2026-10-02, `n_test` = 672 out-of-sample forecasts.

| | Accuracy |
|---|---|
| Model (move-xgb, version 8) | 53.72% |
| Baseline: always quiet | 55.65% |
| Baseline: previous move | 55.51% |

Precision 0.4807, recall 0.5436, F1 0.5102, with "large" as the positive class. **The model is
worse than always guessing quiet**, and version 8 was rejected under the rule in force when
it ran (section 5). The test period was calmer than the
training history, which is why quiet weeks were more common than half.

Every version trained, newest first:

| Version | Task | Algorithm | Accuracy | Status |
|---|---|---|---|---|
| 8 | move | XGBoost | 0.5372 | rejected |
| 7 | direction | XGBoost | 0.4955 | rejected |
| 6 | direction | XGBoost | 0.4955 | rejected |
| 5 | direction | XGBoost | 0.4955 | rejected |
| 4 | direction | XGBoost | 0.4955 | rejected |
| 3 | direction | XGBoost | 0.4896 | rejected |
| 2 | direction | Logistic regression | 0.4836 | rejected |
| 1 | direction | Logistic regression | 0.4777 | rejected |

Direction accuracy and move accuracy answer different questions, so the two groups of rows
should not be compared with each other. Versions 4 to 7 are identical reruns from before the
pipeline learned to skip them.

How the other Model performance figures are computed:

- **Weekly accuracy:** share of correct test predictions per week (weeks start Monday), last 12
  weeks.
- **Sharpe ratio and max drawdown:** shown as "—". The move model does not take a side, so
  there is no trade to score.
- **Inference latency:** median time of one single-row prediction on the machine that ran the
  pipeline (3.1 ms). **Cost per request:** none, the model runs locally.

## 5. The gate

A version serves forecasts only if every check in `ml/gate.py` passes. Today there is one:
accuracy is at least **0.52**. Beating the baselines is not required.

The 0.52 threshold was fixed in `ml/config.yaml` at kickoff, before any model result, and has
not been changed. On 2026-10-10 a second check (beat `always_quiet`) was added, and version 8
was rejected under it. That check was then removed, so the next run that clears 0.52 is
promoted even if always-quiet scores higher. A rejected version stays in the registry with `status: "rejected"`, never
serves a forecast, and its number is never rewritten. While nothing passes, `production` and
every stock's `forecast` are `null` and the page says "No forecast".

## 6. Backtest against live

The forecast log has 180 resolved rows (92 correct, 51.1%) and 3 pending rows.

- The **resolved** rows are `origin: "backtest"`: out-of-sample walk-forward test predictions
  for the last 60 test sessions. The model had not trained on those days, but they were
  scored after the fact.
- The **pending** rows are `origin: "live"`: made from the close of 2026-10-09 (typical move
  3.52%), logged before the outcome existed. They resolve after the close on 2026-10-16.
  Only live rows are a true track record. They are logged even when the model fails the gate,
  so the record includes rejected models.

## 7. Limitations

- **Three stocks, picked by hand.** TSLA, NVDA and AAPL are large, well-covered survivors.
  Results may not hold for smaller or delisted companies.
- **Small samples.** 672 test forecasts gives a margin of roughly ±4 points on accuracy, so the
  model and both baselines are not clearly different from each other.
- **Headline-only scoring.** FinBERT reads titles, not articles. It has not been checked against
  hand labels.
- **Reddit coverage is zero** in the current data, as described above.
- **Analyst counts are monthly** and change slowly, so the analyst score lags news.
- **No schedule yet.** The data is whatever the pipeline last published, and live rows only
  accumulate when it is run.
