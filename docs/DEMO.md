# Demo script

About three minutes. Numbers quoted here are from the 2026-10-10 artifacts; read the live ones
off the screen.

## Before you start

- Start the API and web app (see the README), or open the deployed site a few minutes early so
  the API is awake.
- Open the landing page in one tab. Have NVDA in mind: it has the widest gap.

## The walkthrough

| Step | Where | Do | Say |
|---|---|---|---|
| 1 | Landing page | Let the headline sit for a second, then point at the product window. | "Normal finance sites show you a price. This shows you who disagrees about it. That window is live data, not a mock-up: it picks whichever stock has the widest gap right now." |
| 2 | Landing page | Scroll to "The gap is the story". | "All three stocks on one scale. NVDA's groups are 40 points apart; Tesla's are 3." |
| 3 | Landing page | Scroll to "The receipts". | "And this is the part most projects hide. Our model estimates whether next week is a bigger move than usual, and it's right 53.7% of the time. Always guessing 'quiet week' gets 55.7%. Zero of eight versions passed our quality gate." |
| 4 | Dashboard | Click "Open the dashboard", choose NVDA. | "Price on the left. On the right, where a forecast would be, it says 'No forecast', because no model passed the gate. We show nothing instead of a guess that failed its own test." |
| 5 | Dashboard | Point at the sentiment card. | "Analysts at +55, news at +15. The analyst column says 'ratings consensus' because it comes from buy and sell counts, not text." |
| 6 | Dashboard | Scroll to the headlines, open one. | "Every score links back to the headlines that produced it." |
| 7 | Model performance | Click the tab. | "The report card. Accuracy beside both baselines, on 672 forecasts the model had never seen." |
| 8 | Model performance | Scroll to the registry. | "Every version we trained, tracked in MLflow, each marked rejected. The gate was fixed at 52% before we saw any result, so we could not tune it to pass." |
| 9 | Model performance | Scroll to the forecast log. | "Hits and misses, none removed. These are labelled 'backtest'; live forecasts need five trading days to resolve." |
| 10 | Alerts | Click the tab, type an email, pick a trigger, create. | "Sign up for a stock and a trigger. The example email on the right is built from today's data. It is stored, not sent: that is the next step." |

## If someone asks

| Question | Answer |
|---|---|
| "So the model doesn't work?" | "It doesn't beat a trivial baseline, and the site says so. Five-day direction was a coin flip, and move size so far loses to always guessing quiet. What we built is the pipeline that measures that honestly: walk-forward validation, a fixed gate, a public log." |
| "Where's Reddit?" | "The ingestion is written, but Reddit is missing from this data, most likely because it refused our requests. We leave a source out instead of inventing a score." |
| "Is the data live?" | "It is real data from the last pipeline run. It is not yet refreshed on a schedule." |
| "What did the AI agents do?" | "Each of us worked with a coding agent. We fixed a JSON contract first, with a validator, so the two sides could be built separately and still fit." |
| "What's the MCP server?" | "It lets an AI assistant query our sentiment and track record directly. Same data as the site." |

## If something breaks

| Problem | Do |
|---|---|
| "Can't reach the SentiFi API" | The API is asleep or stopped. Wait a few seconds and click Retry. |
| Fonts or colours look wrong locally | Stop the web server, delete `web/.next`, start it again. |
| The "Why do they disagree?" panel says it is not set up | Expected without an Anthropic key. Skip it. |
