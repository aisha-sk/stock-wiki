"use client";

import { getModel } from "@/lib/api";
import { formatThreshold, formatVersion } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useSelectedStock } from "@/lib/useSelectedStock";
import { ForecastLog } from "./ForecastLog";
import { MetricCards } from "./MetricCards";
import { RegistryTable } from "./RegistryTable";
import { ErrorCard } from "../ui/ErrorCard";
import { Loading, Skeleton } from "../ui/Skeleton";
import { WeeklyAccuracyChart } from "./WeeklyAccuracyChart";

export function ModelPerformance() {
  const { selected } = useSelectedStock();
  const model = useApi("model", getModel);

  if (model.status === "loading") {
    return (
      <Loading label="Loading model performance">
        <Skeleton className="h-[120px]" />
        <div className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-[120px]" />
          ))}
        </div>
        <Skeleton className="h-[300px]" />
      </Loading>
    );
  }
  if (model.status === "error") {
    return <ErrorCard what="model performance" error={model.error} onRetry={model.reload} />;
  }

  const { production, versions, task, gate } = model.data;
  const latest = versions[0];
  const subject = production
    ? `${production.model_name} ${formatVersion(production.version)}`
    : latest
      ? `${latest.model_name} ${formatVersion(latest.version)}`
      : null;

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-wrap items-center justify-between gap-x-8 gap-y-3 rounded-xl border border-line bg-card p-6">
        <div className="min-w-0 flex-[1_1_480px]">
          <h1 className="mb-1 font-display text-3xl font-medium">Model performance</h1>
          <p className="text-[15px] text-muted">
            {production
              ? `${subject} is serving forecasts. `
              : `No version has passed the quality gate, so no forecast is being served. The gate is ${formatThreshold(gate.threshold)} accuracy and beating the always-quiet baseline. `}
            {!production && subject && `The numbers below are for the latest candidate, ${subject}. `}
            The question it answers: {task.description} Sentiment scores come from a separate model and describe
            what people are saying; they are not a forecast.
          </p>
        </div>
        <div
          className={`rounded-2xl border px-3 py-1.5 text-sm font-medium ${
            production ? "border-bull text-bull" : "border-bear text-bear"
          }`}
        >
          {production ? "Production · passed quality gate" : "No production model"}
        </div>
      </section>

      <MetricCards model={model.data} />

      <div className="flex flex-wrap gap-6">
        <WeeklyAccuracyChart weeks={model.data.weekly_accuracy} gate={gate} />
        <RegistryTable versions={versions} gate={gate} />
      </div>

      {selected && <ForecastLog symbol={selected.symbol} />}
    </div>
  );
}
