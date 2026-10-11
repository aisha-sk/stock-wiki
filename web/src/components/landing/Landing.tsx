"use client";

import Link from "next/link";
import { getAlertPreview, getForecasts, getModel, getStock, getTickers } from "@/lib/api";
import {
  capitalize,
  formatDateTime,
  formatPct,
  formatPrice,
  formatRate,
  formatScore,
  formatThreshold,
  formatVersion,
  labelColor,
} from "@/lib/format";
import type { AlertPreview, Forecasts, Model, Source, Stock } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { SentimentCard } from "../SentimentCard";
import { ErrorCard } from "../ui/ErrorCard";
import { Skeleton } from "../ui/Skeleton";
import { CountUp } from "./CountUp";
import { Reveal } from "./Reveal";

interface LandingData {
  stocks: Stock[];
  /** The stock whose groups disagree most right now. */
  lead: Stock;
  model: Model;
  forecasts: Forecasts;
  preview: AlertPreview;
}

async function getLanding(): Promise<LandingData> {
  const [{ tickers }, model, forecasts] = await Promise.all([getTickers(), getModel(), getForecasts({ limit: 1 })]);
  const stocks = await Promise.all(tickers.map((ticker) => getStock(ticker.symbol)));
  const lead = stocks.reduce((best, stock) =>
    (stock.sentiment.gap?.points ?? -1) > (best.sentiment.gap?.points ?? -1) ? stock : best,
  );
  return { stocks, lead, model, forecasts, preview: await getAlertPreview(lead.symbol) };
}

const SHORT_NAME: Record<Source, string> = { analysts: "Analysts", news: "News", reddit: "Reddit" };

const primaryButton =
  "flex min-h-12 items-center rounded-full bg-ink px-6 text-base font-medium text-white hover:opacity-90";
const secondaryButton =
  "flex min-h-12 items-center rounded-full border border-control bg-card px-6 text-base font-medium hover:border-ink";

/** The real product, framed like a window, as the page's hero image. */
function ProductWindow({ stock }: { stock: Stock }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-page shadow-[0_30px_80px_-30px_rgba(17,21,27,0.35)]">
      <div className="flex items-center gap-3 border-b border-line bg-card px-4 py-3">
        <div aria-hidden="true" className="flex gap-1.5">
          <span className="size-2.5 rounded-full bg-line" />
          <span className="size-2.5 rounded-full bg-line" />
          <span className="size-2.5 rounded-full bg-line" />
        </div>
        <div className="flex flex-1 flex-wrap items-baseline justify-between gap-x-4 text-sm">
          <span className="text-muted">
            {stock.symbol} · {stock.name}
          </span>
          <span className="font-mono">
            {formatPrice(stock.quote.price)}{" "}
            <span className={stock.quote.change_pct >= 0 ? "text-bull" : "text-bear"}>
              {formatPct(stock.quote.change_pct)}
            </span>
          </span>
        </div>
      </div>
      <div className="p-4 text-left sm:p-6">
        <SentimentCard
          symbol={stock.symbol}
          sentiment={stock.sentiment}
          headlines={stock.headlines}
          maxHeadlines={3}
        />
      </div>
    </div>
  );
}

/** Every tracked stock on one scale, so the widest gap is obvious at a glance. */
function GapBoard({ stocks }: { stocks: Stock[] }) {
  return (
    <div className="flex flex-col gap-5 rounded-2xl border border-line bg-card p-6">
      {stocks.map((stock) => {
        const { sources, gap } = stock.sentiment;
        return (
          <Link key={stock.symbol} href={`/dashboard?symbol=${stock.symbol}`} className="group flex flex-col gap-1.5">
            <div className="flex items-baseline justify-between gap-3">
              <span className="font-mono font-medium group-hover:underline">{stock.symbol}</span>
              <span className="text-sm text-muted">{gap ? `${gap.points}-point gap` : "one source so far"}</span>
            </div>
            <div
              role="img"
              aria-label={sources.map((s) => `${s.display_name} ${formatScore(s.score)}`).join(", ")}
              className="relative h-6"
            >
              <div className="absolute inset-x-0 top-2 h-2 rounded bg-[linear-gradient(90deg,var(--color-bear),var(--color-line)_50%,var(--color-bull))]" />
              {sources.map((source) => (
                <div
                  key={source.source}
                  className="marker-in absolute top-0 -ml-0.5 h-6 w-1 rounded-sm bg-ink ring-2 ring-card"
                  style={{ left: `${(source.score + 100) / 2}%` }}
                />
              ))}
            </div>
            <div className="text-[13px] text-muted">
              {sources.map((s) => `${SHORT_NAME[s.source]} ${formatScore(s.score)}`).join(" · ")}
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function HeadlineStack({ stock }: { stock: Stock }) {
  // One headline per group first, so both sides of the story show.
  const seen = new Set<Source>();
  const picks = stock.headlines.filter((h) => !seen.has(h.source) && seen.add(h.source));
  const rest = stock.headlines.filter((h) => !picks.includes(h));
  return (
    <div className="flex flex-col gap-3">
      {[...picks, ...rest].slice(0, 3).map((headline, index) => (
        <div
          key={headline.id}
          className="rounded-2xl border border-line bg-card p-5"
          style={{ marginLeft: `${index * 20}px` }}
        >
          <div className="mb-1 flex items-baseline justify-between gap-3 text-[13px]">
            <span className="font-semibold text-muted">{SHORT_NAME[headline.source]}</span>
            <span className={labelColor(headline.label)}>{capitalize(headline.label)}</span>
          </div>
          <div className="font-display text-lg leading-snug">{headline.title}</div>
          <div className="mt-1 text-[13px] text-muted">
            {headline.publisher} · {formatDateTime(headline.published_at)}
          </div>
        </div>
      ))}
    </div>
  );
}

function EmailCard({ preview }: { preview: AlertPreview }) {
  return (
    <div className="rounded-2xl border border-line bg-card p-6">
      <div className="mb-3 flex items-center gap-3 border-b border-line pb-3 text-[13px] text-muted">
        <span aria-hidden="true" className="flex size-8 items-center justify-center rounded-full bg-ink text-white">
          S
        </span>
        StockSense alerts
      </div>
      <div className="font-display text-xl font-medium">{preview.subject}</div>
      {preview.body_lines.map((line) => (
        <p key={line} className="mt-2 text-[15px] leading-relaxed">
          {line}
        </p>
      ))}
      <p className="mt-3 text-[13px] text-muted">Not financial advice.</p>
    </div>
  );
}

function Feature({
  kicker,
  title,
  body,
  visual,
  flip = false,
}: {
  kicker: string;
  title: string;
  body: string;
  visual: React.ReactNode;
  flip?: boolean;
}) {
  return (
    <Reveal className="grid items-center gap-x-16 gap-y-8 md:grid-cols-2">
      <div className={flip ? "md:order-2" : ""}>
        <div className="mb-3 text-sm font-medium uppercase tracking-widest text-muted">{kicker}</div>
        <h2 className="font-display text-4xl leading-tight sm:text-[44px]">{title}</h2>
        <p className="mt-4 max-w-[46ch] text-lg leading-relaxed text-muted">{body}</p>
      </div>
      <div className="min-w-0">{visual}</div>
    </Reveal>
  );
}

function Scorecard({ model, forecasts }: { model: Model; forecasts: Forecasts }) {
  const alwaysQuiet = model.baselines.find((b) => b.name === "always_quiet");
  const passed = model.versions.filter((v) => v.gate_passed).length;
  const logged = forecasts.summary.resolved + forecasts.summary.pending;
  const whole = (value: number) => String(Math.round(value));
  const stats = [
    {
      value: <CountUp value={model.metrics.directional_accuracy} format={(v) => formatRate(v)} />,
      label: "of 5-day calls were right",
      note: `${model.task.n_test} out-of-sample forecasts`,
    },
    alwaysQuiet && {
      value: <CountUp value={alwaysQuiet.directional_accuracy} format={(v) => formatRate(v)} />,
      label: "is what always guessing “quiet” scores",
      note: "a version must beat it to be promoted",
    },
    {
      value: (
        <>
          <CountUp value={passed} format={whole} /> of <CountUp value={model.versions.length} format={whole} />
        </>
      ),
      label: "model versions passed the quality gate",
      note: `the gate is ${formatThreshold(model.gate.threshold)} accuracy and beating “always quiet”`,
    },
    {
      value: <CountUp value={logged} format={whole} />,
      label: "forecasts on the public log",
      note: "hits and misses, none removed",
    },
  ].filter((stat) => !!stat);

  return (
    <section className="bg-ink text-white">
      <div className="mx-auto max-w-[1200px] px-6 py-24">
        <Reveal>
          <div className="mb-3 text-sm font-medium uppercase tracking-widest text-ink-soft">The receipts</div>
          <h2 className="max-w-[18ch] font-display text-4xl leading-tight sm:text-[56px]">
            We grade our own forecasts, in public.
          </h2>
          <p className="mt-5 max-w-[60ch] text-lg leading-relaxed text-ink-soft">
            {model.production
              ? `${model.production.model_name} ${formatVersion(model.production.version)} passed the gate and is serving forecasts. `
              : "Right now no version has passed the gate, so StockSense shows no forecast at all. We would rather show nothing than a guess that failed its own test. "}
            Predicting five days ahead is close to a coin flip, and the numbers below say so.
          </p>
        </Reveal>
        <Reveal>
          <dl className="mt-14 grid gap-x-10 gap-y-12 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat) => (
              <div key={stat.label} className="border-t border-white/20 pt-5">
                <dd className="font-mono text-5xl font-medium tracking-tight">{stat.value}</dd>
                <dt className="mt-3 text-base">{stat.label}</dt>
                <div className="mt-1 text-sm text-ink-soft">{stat.note}</div>
              </div>
            ))}
          </dl>
        </Reveal>
        <Link
          href="/model"
          className="mt-12 inline-flex min-h-12 items-center rounded-full border border-white/40 px-6 font-medium hover:border-white"
        >
          See the full report card
        </Link>
      </div>
    </section>
  );
}

const STEPS = [
  {
    title: "Collect",
    body: "We gather what each group is publishing about a stock: analyst ratings, news headlines and forum posts.",
  },
  {
    title: "Score",
    body: "A finance-trained language model reads every headline and scores it from −100, bearish, to +100, bullish.",
  },
  {
    title: "Forecast, then grade",
    body: "A separate model estimates the next five trading days. Every call is logged before the outcome exists, then marked hit or miss.",
  },
];

export function Landing() {
  const landing = useApi("landing", getLanding);
  const data = landing.data;

  return (
    <main className="flex flex-1 flex-col">
      <section className="mx-auto w-full max-w-[1200px] px-6 pb-24 pt-16 text-center sm:pt-24">
        <div className="mb-6 inline-flex min-h-8 items-center rounded-full border border-line bg-card px-4 text-sm text-muted">
          {data ? `Tracking ${data.stocks.map((s) => s.symbol).join(", ")}` : "Sentiment, compared"}
        </div>
        <h1 className="mx-auto max-w-[16ch] font-display text-5xl leading-[1.05] tracking-tight sm:text-7xl">
          Wall Street says one thing. <em>The headlines say another.</em>
        </h1>
        <p className="mx-auto mt-6 max-w-[58ch] text-lg leading-relaxed text-muted sm:text-xl">
          StockSense shows how each group feels about a stock and how far apart they are. Then it forecasts the
          next five days and grades itself in public.
        </p>
        <div className="mt-9 flex flex-wrap justify-center gap-3">
          <Link href="/dashboard" className={primaryButton}>
            Open the dashboard
          </Link>
          <Link href="/alerts" className={secondaryButton}>
            Get alerts
          </Link>
        </div>

        <div className="mx-auto mt-16 max-w-[1040px]">
          {landing.status === "loading" && <Skeleton className="h-[360px] rounded-2xl" />}
          {landing.status === "error" && (
            <ErrorCard what="the live preview" error={landing.error} onRetry={landing.reload} />
          )}
          {data && <ProductWindow stock={data.lead} />}
          {data && (
            <p className="mt-4 text-sm text-muted">
              Live data for {data.lead.symbol}, the widest disagreement we are tracking right now.
            </p>
          )}
        </div>
      </section>

      {data && (
        <section className="mx-auto flex w-full max-w-[1200px] flex-col gap-28 px-6 py-24">
          <Feature
            kicker="The spectrum"
            title="The gap is the story."
            body="A price tells you where a stock is. The distance between the people watching it tells you what they are arguing about. Every stock sits on the same scale, so the widest gap stands out."
            visual={<GapBoard stocks={data.stocks} />}
          />
          <Feature
            flip
            kicker="The evidence"
            title="Read what each side is reading."
            body="A score with nothing behind it is a mood ring. Each one links to the headlines that produced it, with the source and the label it was given."
            visual={<HeadlineStack stock={data.lead} />}
          />
          <Feature
            kicker="The alert"
            title="Hear about it when the mood turns."
            body="Nobody wants to check a dashboard every day. Pick a stock and a trigger, and we will tell you when the groups pull apart or flip sides."
            visual={<EmailCard preview={data.preview} />}
          />
        </section>
      )}

      {data && <Scorecard model={data.model} forecasts={data.forecasts} />}

      <section className="mx-auto w-full max-w-[1200px] px-6 py-24">
        <Reveal>
          <h2 className="font-display text-4xl leading-tight sm:text-[44px]">How it works</h2>
          <ol className="mt-12 grid gap-x-12 gap-y-10 md:grid-cols-3">
            {STEPS.map((step, index) => (
              <li key={step.title} className="border-t border-ink pt-5">
                <div className="font-display text-5xl text-muted">{index + 1}</div>
                <h3 className="mt-3 text-xl font-semibold">{step.title}</h3>
                <p className="mt-2 text-base leading-relaxed text-muted">{step.body}</p>
              </li>
            ))}
          </ol>
        </Reveal>
      </section>

      <section className="mx-auto w-full max-w-[1200px] px-6 pb-24">
        <Reveal className="rounded-3xl border border-line bg-card px-6 py-16 text-center">
          <h2 className="mx-auto max-w-[20ch] font-display text-4xl leading-tight sm:text-[52px]">
            See who disagrees about your stock.
          </h2>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/dashboard" className={primaryButton}>
              Open the dashboard
            </Link>
            <Link href="/alerts" className={secondaryButton}>
              Get alerts
            </Link>
          </div>
        </Reveal>
      </section>
    </main>
  );
}
