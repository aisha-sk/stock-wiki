import {
  formatCost,
  formatDecimal,
  formatLatency,
  formatRate,
  formatSignedRate,
  orDash,
} from "@/lib/format";
import type { Model } from "@/lib/types";

const BASELINE_NAME = { always_up: "always up", previous_direction: "previous direction" } as const;

export function MetricCards({ model }: { model: Model }) {
  const { metrics, baselines, task } = model;
  const cards = [
    {
      group: "Predictive",
      value: formatRate(metrics.directional_accuracy),
      label: "Directional accuracy",
      note: [
        ...baselines.map((b) => `${BASELINE_NAME[b.name]} ${formatRate(b.directional_accuracy)}`),
        `${task.n_test} test forecasts`,
      ].join(" · "),
    },
    { group: "Predictive", value: formatDecimal(metrics.precision), label: "Precision" },
    { group: "Predictive", value: formatDecimal(metrics.recall), label: "Recall" },
    { group: "Predictive", value: formatDecimal(metrics.f1), label: "F1-score" },
    {
      group: "Financial, if traded",
      value: orDash(metrics.sharpe_ratio, formatDecimal),
      label: "Sharpe ratio",
    },
    {
      group: "Financial, if traded",
      value: orDash(metrics.max_drawdown, formatSignedRate),
      label: "Max drawdown",
    },
    {
      group: "System",
      value: orDash(metrics.inference_latency_ms, formatLatency),
      label: "Inference latency",
    },
    {
      group: "System",
      value: orDash(metrics.cost_per_request_usd, formatCost),
      label: "Cost per request",
      note: metrics.cost_per_request_usd === null ? "Runs locally, no per-request cost" : undefined,
    },
  ];

  return (
    <dl className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4">
      {cards.map((card) => (
        <div key={card.label} className="rounded-xl border border-line bg-card px-5 py-4">
          <div className="text-[13px] text-muted">{card.group}</div>
          <dd className="my-1 font-mono text-[28px] font-medium">{card.value}</dd>
          <dt className="text-sm">{card.label}</dt>
          {card.note && <div className="mt-1 text-[13px] text-muted">{card.note}</div>}
        </div>
      ))}
    </dl>
  );
}
