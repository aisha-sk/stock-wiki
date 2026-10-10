"use client";

import { useState } from "react";
import { getForecasts } from "@/lib/api";
import { capitalize, formatDate, formatPct, formatRate } from "@/lib/format";
import type { ForecastRow, ForecastSummary } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const RESULT_STYLE = { hit: "text-bull", miss: "text-bear" } as const;

function summarize(summary: ForecastSummary) {
  const pending = summary.pending > 0 ? ` ${summary.pending} pending.` : "";
  if (summary.resolved === 0 || summary.hit_rate === null) return `No resolved forecasts yet.${pending}`;
  return `${summary.hits} of ${summary.resolved} resolved forecasts correct (${formatRate(summary.hit_rate)}).${pending}`;
}

function Row({ row }: { row: ForecastRow }) {
  return (
    <tr className="border-t border-line">
      <td className="py-3 pr-2 font-mono">{row.symbol}</td>
      <td className="px-2 py-3">{formatDate(row.as_of_date)}</td>
      <td className="px-2 py-3">{capitalize(row.direction)}</td>
      <td className="px-2 py-3">
        {row.actual_direction && row.actual_return_pct !== null
          ? `${capitalize(row.actual_direction)} ${formatPct(row.actual_return_pct, 1)}`
          : `Resolves ${formatDate(row.target_date)}`}
      </td>
      <td className={`px-2 py-3 font-semibold ${row.result ? RESULT_STYLE[row.result] : "font-normal text-muted"}`}>
        {row.result ? capitalize(row.result) : "Pending"}
      </td>
      <td className="py-3 pl-2">
        <span className="rounded-full border border-line px-2 py-0.5 text-xs text-muted">{row.origin}</span>
      </td>
    </tr>
  );
}

export function ForecastLog({ symbol }: { symbol: string }) {
  const [onlySelected, setOnlySelected] = useState(false);
  const scope = onlySelected ? symbol : undefined;
  const log = useApi(`forecasts:${scope ?? "all"}`, () => getForecasts({ symbol: scope }));
  const total = log.data ? log.data.summary.resolved + log.data.summary.pending : 0;

  const pill = (active: boolean) =>
    `min-h-11 rounded-full border px-4 text-sm font-medium ${
      active ? "border-ink bg-ink text-white" : "border-control bg-card text-ink hover:border-ink"
    }`;

  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-card p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-[17px] font-semibold">Recent forecasts vs. what happened</h2>
        <div role="group" aria-label="Which forecasts to show" className="flex gap-2">
          <button aria-pressed={!onlySelected} onClick={() => setOnlySelected(false)} className={pill(!onlySelected)}>
            All stocks
          </button>
          <button aria-pressed={onlySelected} onClick={() => setOnlySelected(true)} className={pill(onlySelected)}>
            {symbol} only
          </button>
        </div>
      </div>

      {log.status === "loading" && <p className="text-[15px] text-muted">Loading forecasts…</p>}
      {log.status === "error" && (
        <div role="alert" className="flex flex-wrap items-center gap-3 text-[15px]">
          <span>Couldn&apos;t load the forecast log. {log.error.message}</span>
          <button onClick={log.reload} className="min-h-11 rounded-lg border border-ink px-4 font-medium">
            Retry
          </button>
        </div>
      )}
      {log.status === "ready" && (
        <>
          <p className="text-[15px]">
            <span className="font-semibold">{summarize(log.data.summary)}</span>
            {total > log.data.forecasts.length && ` Showing the latest ${log.data.forecasts.length} of ${total}.`}
          </p>
          {log.data.forecasts.length === 0 ? (
            <p className="text-[15px] text-muted">No forecasts have been logged yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[620px] border-collapse text-sm">
                <thead>
                  <tr className="text-left text-muted">
                    <th className="py-2 pr-2 font-medium">Stock</th>
                    <th className="p-2 font-medium">Forecast made</th>
                    <th className="p-2 font-medium">Called</th>
                    <th className="p-2 font-medium">Actual, 5 days later</th>
                    <th className="p-2 font-medium">Result</th>
                    <th className="py-2 pl-2 font-medium">Origin</th>
                  </tr>
                </thead>
                <tbody>
                  {log.data.forecasts.map((row) => (
                    <Row key={row.id} row={row} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="text-[13px] text-muted">
            Backtest rows are out-of-sample test predictions: the model had not seen those days when it made
            them. Live rows were logged before the outcome existed, and only they are a true track record.
          </p>
        </>
      )}
    </section>
  );
}
