import Link from "next/link";
import { capitalize, formatDate, formatDateTime, formatRate, formatVersion } from "@/lib/format";
import type { Forecast } from "@/lib/types";

export function ForecastCard({ symbol, forecast }: { symbol: string; forecast: Forecast | null }) {
  const trackRecord = (
    <Link href={`/model?symbol=${symbol}`} className="text-white underline underline-offset-2">
      Model performance
    </Link>
  );

  return (
    <section
      aria-label="Model forecast"
      className="flex min-w-0 flex-[1_1_280px] flex-col gap-3 rounded-xl bg-ink p-6 text-white"
    >
      {forecast ? (
        <>
          <h2 className="text-sm font-normal text-ink-soft">
            Model forecast · next {forecast.horizon_days} trading days
          </h2>
          <div className="text-4xl font-semibold">{capitalize(forecast.direction)}</div>
          <div className="text-[15px] text-ink-soft">
            Model confidence <span className="font-mono text-white">{formatRate(forecast.confidence, 0)}</span>
          </div>
          <div
            role="meter"
            aria-label="Model confidence"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(forecast.confidence * 100)}
            className="h-2 rounded bg-[#3a424f]"
          >
            <div className="h-2 rounded bg-white" style={{ width: formatRate(forecast.confidence, 0) }} />
          </div>
          <p className="mt-2 text-[13px] leading-relaxed text-ink-soft">
            {forecast.model_name} {formatVersion(forecast.model_version)} · made{" "}
            {formatDateTime(forecast.made_at)} · resolves {formatDate(forecast.target_date)}. An estimate, not
            advice. Its track record is on {trackRecord}.
          </p>
        </>
      ) : (
        <>
          <h2 className="text-sm font-normal text-ink-soft">Model forecast</h2>
          <div className="text-4xl font-semibold">No forecast</div>
          <p className="text-[15px] leading-relaxed text-ink-soft">
            No model version has passed the quality gate yet. See {trackRecord}.
          </p>
        </>
      )}
    </section>
  );
}
