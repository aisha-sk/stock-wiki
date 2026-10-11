"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatDate, formatPrice } from "@/lib/format";
import type { TooltipContentProps } from "recharts";
import type { PricePoint } from "@/lib/types";

export const SESSIONS_SHOWN = 20;

interface Row {
  label: string;
  close: number;
}

function ChartTooltip({ active, payload }: TooltipContentProps) {
  const row = payload?.[0]?.payload as Row | undefined;
  if (!active || !row) return null;
  return (
    <div className="rounded-lg border border-line bg-card px-3 py-2 text-[13px] shadow-sm">
      <div className="text-muted">{formatDate(row.label, true)}</div>
      <div className="font-mono text-[15px]">{formatPrice(row.close)}</div>
    </div>
  );
}

export function PriceChart({ symbol, prices }: { symbol: string; prices: PricePoint[] }) {
  const visible = prices.slice(-SESSIONS_SHOWN);
  const closes = visible.map((p) => p.close);
  const low = Math.min(...closes);
  const high = Math.max(...closes);
  const range = high - low || high * 0.01;
  const last = visible[visible.length - 1];
  const rows: Row[] = visible.map((p) => ({ label: p.date, close: p.close }));
  const pad = range * 0.12;
  const domain = [low - pad, high + pad];
  const dateTicks = [visible[0].date, visible[Math.floor(visible.length / 2)].date, last.date];
  const summary =
    `${symbol} closing price over the last ${visible.length} sessions, ` +
    `from ${formatPrice(visible[0].close)} to ${formatPrice(last.close)}.`;

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
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
