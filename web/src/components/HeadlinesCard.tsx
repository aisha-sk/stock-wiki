import { capitalize, formatDateTime, labelColor } from "@/lib/format";
import type { Headline, Source } from "@/lib/types";

const SOURCE_NAME: Record<Source, string> = {
  analysts: "Wall Street",
  news: "News media",
  reddit: "Reddit",
};

export function HeadlinesCard({ headlines }: { headlines: Headline[] }) {
  return (
    <section aria-labelledby="headlines-title" className="rounded-xl border border-line bg-card p-6">
      <h2 id="headlines-title" className="mb-4 font-display text-2xl font-medium">
        What each side is reading
      </h2>
      {headlines.length === 0 ? (
        <p className="text-[15px] text-muted">No headlines to show yet.</p>
      ) : (
        <ul>
          {headlines.map((headline) => (
            <li
              key={headline.id}
              className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t border-line py-3"
            >
              <span className="flex-[0_0_120px] text-[13px] font-semibold text-muted">
                {SOURCE_NAME[headline.source]}
              </span>
              <div className="min-w-0 flex-[1_1_320px]">
                {headline.url ? (
                  <a
                    href={headline.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline decoration-line underline-offset-4 hover:decoration-ink"
                  >
                    {headline.title}
                  </a>
                ) : (
                  <span>{headline.title}</span>
                )}
                <div className="text-[13px] text-muted">
                  {headline.publisher} · {formatDateTime(headline.published_at)}
                </div>
              </div>
              <span className={`flex-[0_0_80px] text-right text-[13px] ${labelColor(headline.label)}`}>
                {capitalize(headline.label)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
