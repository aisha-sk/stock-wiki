import Link from "next/link";
import { capitalize, formatScore, labelColor } from "@/lib/format";
import type { Headline, Label, Sentiment } from "@/lib/types";

function counts(items: Headline[]) {
  const tally: Record<Label, number> = { bullish: 0, neutral: 0, bearish: 0 };
  for (const item of items) tally[item.label] += 1;
  return tally;
}

function SourceColumn({ title, items, empty }: { title: string; items: Headline[]; empty: string }) {
  const tally = counts(items);
  return (
    <div className="flex min-w-0 flex-[1_1_240px] flex-col gap-3">
      <h3 className="text-[15px] font-semibold">{title}</h3>
      {items.length === 0 ? (
        <p className="text-[13px] text-muted">{empty}</p>
      ) : (
        <>
          <p className="text-[13px] text-muted">
            {tally.bullish} bullish · {tally.neutral} neutral · {tally.bearish} bearish
          </p>
          <ul className="flex flex-col gap-2">
            {items.map((item) => (
              <li key={item.id} className="text-[14px] leading-snug">
                <span className={`font-medium ${labelColor(item.label)}`}>{capitalize(item.label)}</span>
                <span className="text-ink"> · {item.title}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export function SentimentCard({
  symbol,
  sentiment,
  headlines,
}: {
  symbol: string;
  sentiment: Sentiment;
  headlines: Headline[];
}) {
  const { gap } = sentiment;
  const analysts = sentiment.sources.find((source) => source.source === "analysts");
  const news = headlines.filter((item) => item.source === "news");
  const reddit = headlines.filter((item) => item.source === "reddit");
  return (
    <section aria-labelledby="spectrum-title" className="flex flex-col gap-5 rounded-xl border border-line bg-card p-6">
      <div className="flex flex-wrap justify-between gap-2">
        <h2 id="spectrum-title" className="text-xl font-semibold">
          Wall Street, news and Reddit
        </h2>
        <p className="text-sm text-muted">Each item labelled bullish, neutral, or bearish</p>
      </div>

      <div className="flex flex-wrap gap-6">
        <div className="flex min-w-0 flex-[1_1_240px] flex-col gap-3">
          <h3 className="text-[15px] font-semibold">Wall Street analysts</h3>
          {analysts ? (
            <>
              <p className={`font-mono text-[15px] ${labelColor(analysts.label)}`}>
                {formatScore(analysts.score)} {capitalize(analysts.label)}
              </p>
              <p className="text-[13px] text-muted">{analysts.note} · ratings consensus</p>
            </>
          ) : (
            <p className="text-[13px] text-muted">No analyst ratings available.</p>
          )}
        </div>
        <SourceColumn title="News" items={news} empty={`No news articles in the last ${sentiment.window_days} days.`} />
        <SourceColumn title="Reddit" items={reddit} empty={`No Reddit posts in the last ${sentiment.window_days} days.`} />
        <div className="flex min-w-0 flex-[1_1_240px] flex-col gap-3">
          <h3 className="text-[15px] font-semibold">Explanation</h3>
          <p className="text-[13px] text-muted">An explanation of the gap will go here.</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        <p className="text-[15px]">
          {gap ? (
            <>
              <span className="font-semibold">Perspective gap: {gap.points} points.</span> {gap.summary}
            </>
          ) : (
            <span className="text-muted">The gap needs at least two groups.</span>
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
