import Link from "next/link";
import { capitalize, formatScore, labelColor } from "@/lib/format";
import type { Sentiment, SentimentSource } from "@/lib/types";

function SpectrumRow({ source }: { source: SentimentSource }) {
  // Score runs -100 to 100; the bar runs 0% to 100%.
  const position = (source.score + 100) / 2;
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
      <div className="min-w-0 flex-[1_1_200px]">
        <div className="flex flex-wrap items-center gap-2 font-medium">
          {source.display_name}
          {source.method === "ratings" && (
            <span className="rounded-full border border-line px-2 py-0.5 text-xs font-normal text-muted">
              ratings consensus
            </span>
          )}
        </div>
        <div className="text-[13px] text-muted">{source.note}</div>
      </div>
      <div
        role="img"
        aria-label={`${source.display_name}: ${formatScore(source.score)}, ${source.label}`}
        className="relative h-7 min-w-0 flex-[3_1_320px]"
      >
        <div className="absolute inset-x-0 top-2.5 h-2 rounded bg-[linear-gradient(90deg,var(--color-bear),var(--color-line)_50%,var(--color-bull))]" />
        <div
          className="absolute top-0.5 -ml-0.5 h-6 w-1 rounded-sm bg-ink ring-2 ring-card"
          style={{ left: `${position}%` }}
        />
      </div>
      <div className={`font-mono text-[15px] md:flex-[0_0_120px] md:text-right ${labelColor(source.label)}`}>
        {formatScore(source.score)} {capitalize(source.label)}
      </div>
    </div>
  );
}

export function SentimentCard({ symbol, sentiment }: { symbol: string; sentiment: Sentiment }) {
  const { sources, gap } = sentiment;
  return (
    <section
      aria-labelledby="spectrum-title"
      className="flex flex-col gap-5 rounded-xl border border-line bg-card p-6"
    >
      <div className="flex flex-wrap justify-between gap-2">
        <h2 id="spectrum-title" className="text-xl font-semibold">
          Sentiment spectrum
        </h2>
        <p className="text-sm text-muted">Bearish ← → Bullish, scored from −100 to +100</p>
      </div>

      {sources.length === 0 ? (
        <p className="text-[15px] text-muted">No sentiment data in the last {sentiment.window_days} days.</p>
      ) : (
        sources.map((source) => <SpectrumRow key={source.source} source={source} />)
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        <p className="text-[15px]">
          {gap && (
            <>
              <span className="font-semibold">Perspective gap: {gap.points} points.</span> {gap.summary}
            </>
          )}
        </p>
        <Link
          href={`/alerts?symbol=${symbol}`}
          className="flex min-h-11 items-center rounded-lg border border-ink bg-card px-4 text-[15px] font-medium"
        >
          Alert me when this shifts
        </Link>
      </div>
    </section>
  );
}
