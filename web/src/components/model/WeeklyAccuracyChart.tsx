"use client";

import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TooltipContentProps } from "recharts";
import { formatDate, formatRate, formatThreshold } from "@/lib/format";
import type { Gate, WeeklyAccuracy } from "@/lib/types";

function WeekTooltip({ active, payload }: TooltipContentProps) {
  const week = payload?.[0]?.payload as WeeklyAccuracy | undefined;
  if (!active || !week) return null;
  return (
    <div className="rounded-lg border border-line bg-card px-3 py-2 text-[13px] shadow-sm">
      <div className="text-muted">Week of {formatDate(week.week_start)}</div>
      <div>
        <span className="font-mono text-[15px]">{formatRate(week.accuracy)}</span> (n = {week.n})
      </div>
    </div>
  );
}

export function WeeklyAccuracyChart({ weeks, gate }: { weeks: WeeklyAccuracy[]; gate: Gate }) {
  const above = weeks.filter((week) => week.accuracy >= gate.threshold).length;
  const summary =
    `Weekly directional accuracy for the last ${weeks.length} weeks. ` +
    `${above} of ${weeks.length} weeks were at or above the ${formatThreshold(gate.threshold)} quality gate.`;

  return (
    <section className="flex min-w-0 flex-[1_1_420px] flex-col gap-4 rounded-xl border border-line bg-card p-6">
      <h2 className="text-[17px] font-semibold">Weekly directional accuracy</h2>
      {weeks.length === 0 ? (
        <p className="text-[15px] text-muted">No weekly results yet.</p>
      ) : (
        <div role="img" aria-label={summary} className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={weeks} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap="18%">
              <CartesianGrid vertical={false} stroke="var(--color-line)" />
              <XAxis
                dataKey="week_start"
                tickFormatter={(value: string) => formatDate(value)}
                interval="preserveStartEnd"
                minTickGap={24}
                tick={{ fill: "var(--color-muted)", fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: "var(--color-line)" }}
              />
              <YAxis
                domain={[0, 1]}
                ticks={[0, 0.25, 0.5, 0.75, 1]}
                tickFormatter={(value: number) => formatRate(value, 0)}
                width={44}
                tick={{ fill: "var(--color-muted)", fontSize: 12, fontFamily: "var(--font-mono)" }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip content={WeekTooltip} cursor={{ fill: "var(--color-page)" }} />
              <Bar
                dataKey="accuracy"
                fill="var(--color-ink)"
                radius={[4, 4, 0, 0]}
                maxBarSize={28}
                isAnimationActive={false}
              />
              <ReferenceLine y={gate.threshold} stroke="var(--color-bear)" strokeWidth={2} strokeDasharray="6 5" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <p className="text-[13px] text-muted">
        <span className="font-semibold text-bear">Dashed line:</span> {formatThreshold(gate.threshold)} quality
        gate. Last {weeks.length} weeks, oldest on the left. {above} of {weeks.length} at or above the gate.
      </p>
    </section>
  );
}
