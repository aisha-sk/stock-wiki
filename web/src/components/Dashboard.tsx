"use client";

import { getStock } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useSelectedStock } from "@/lib/useSelectedStock";
import { ForecastCard } from "./ForecastCard";
import { HeadlinesCard } from "./HeadlinesCard";
import { QuoteCard } from "./QuoteCard";
import { SentimentCard } from "./SentimentCard";

export function Dashboard() {
  const { selected } = useSelectedStock();
  const symbol = selected?.symbol ?? null;
  const stock = useApi(symbol && `stock:${symbol}`, () => getStock(symbol ?? ""));

  // The stock selector reports its own loading and error states.
  if (!symbol) return null;

  if (stock.status === "loading") {
    return <p className="text-[15px] text-muted">Loading {symbol}…</p>;
  }
  if (stock.status === "error") {
    return (
      <div role="alert" className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-card p-6">
        <span>
          Couldn&apos;t load {symbol}. {stock.error.message}
        </span>
        <button onClick={stock.reload} className="min-h-11 rounded-lg border border-ink px-4 font-medium">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap gap-6">
        <QuoteCard stock={stock.data} />
        <ForecastCard symbol={stock.data.symbol} forecast={stock.data.forecast} />
      </div>
      <SentimentCard symbol={stock.data.symbol} sentiment={stock.data.sentiment} />
      <HeadlinesCard headlines={stock.data.headlines} />
    </div>
  );
}
