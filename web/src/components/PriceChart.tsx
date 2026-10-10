"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { capitalize, formatDate, formatPrice } from "@/lib/format";
import type { TooltipContentProps } from "recharts";
import type { Forecast, PricePoint } from "@/lib/types";

export const SESSIONS_SHOWN = 20;
const FORECAST_SLOT = "forecast";

interface Row {
  label: string;
  close?: number;
  forecast?: number;
}

function ChartTooltip({ active, payload }: TooltipContentProps) {
  const row = payload?.[0]?.payload as Row | undefined;
  if (!active || !row) return null;
  return (
    <div className="rounded-lg border border-line bg-card px-3 py-2 text-[13px] shadow-sm">
      {row.label === FORECAST_SLOT ? (
        <>
          <div className="font-medium">Model forecast</div>
          <div className="text-muted">Direction only, not a price target</div>
        </>
      ) : (
        <>
          <div className="text-muted">{formatDate(row.label, true)}</div>
          <div className="font-mono text-[15px]">{formatPrice(row.close ?? 0)}</div>
        </>
      )}
    </div>
  );
}

export function PriceChart({
  symbol,
  prices,
  forecast,
}: {
  symbol: string;
  prices: PricePoint[];
  forecast: Forecast | null;
}) {
  const visible = prices.slice(-SESSIONS_SHOWN);
  const closes = visible.map((p) => p.close);
  const low = Math.min(...closes);
  const high = Math.max(...closes);
  const range = high - low || high * 0.01;
  const last = visible[visible.length - 1];

  const rows: Row[] = visible.map((p) => ({ label: p.date, close: p.close }));
  let forecastEnd: number | null = null;
  if (forecast) {
    // A fixed visual step that shows direction. It is not a predicted price.
    forecastEnd = last.close + (forecast.direction === "up" ? 1 : -1) * range * 0.2;
    rows[rows.length - 1].forecast = last.close;
    rows.push({ label: FORECAST_SLOT, forecast: forecastEnd });
  }

  const pad = range * 0.12;
  const domain = [Math.min(low, forecastEnd ?? low) - pad, Math.max(high, forecastEnd ?? high) + pad];
  const forecastColor = forecast?.direction === "up" ? "var(--color-bull)" : "var(--color-bear)";
  const dateTicks = [visible[0].date, visible[Math.floor(visible.length / 2)].date, last.date];

  const summary =
    `${symbol} closing price over the last ${visible.length} sessions, ` +
    `from ${formatPrice(visible[0].close)} to ${formatPrice(last.close)}. ` +
    (forecast
      ? `Model forecast for the next ${forecast.horizon_days} trading days: ${forecast.direction}.`
      : "No model forecast.");

  return (
    <div role="img" aria-label={summary} className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--color-line)" />
          <XAxis
            dataKey="label"
            ticks={dateTicks}
            tickFormatter={(value: string) => formatDate(value)}
            tick={{ fill: "var(--color-muted)", fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: "var(--color-line)" }}
          />
          <YAxis
            domain={domain}
            width={48}
            tickCount={4}
            tickFormatter={(value: number) => value.toFixed(0)}
            tick={{ fill: "var(--color-muted)", fontSize: 12, fontFamily: "var(--font-mono)" }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={ChartTooltip} cursor={{ stroke: "var(--color-control)" }} />
          <Line
            dataKey="close"
            name="Close"
            stroke="var(--color-ink)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, stroke: "var(--color-card)", strokeWidth: 2 }}
            isAnimationActive={false}
          />
          {forecast && (
            <Line
              dataKey="forecast"
              name={`Forecast: ${capitalize(forecast.direction)}`}
              stroke={forecastColor}
              strokeWidth={2.5}
              strokeDasharray="6 5"
              strokeLinecap="round"
              activeDot={false}
              isAnimationActive={false}
              dot={({ cx, cy, index }: { cx?: number; cy?: number; index?: number }) =>
                index === rows.length - 1 && cx != null && cy != null ? (
                  <circle key="end" cx={cx} cy={cy} r={5} fill={forecastColor} />
                ) : (
                  <g key={index} />
                )
              }
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
