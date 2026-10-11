"use client";

import { getStock } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useSelectedStock } from "@/lib/useSelectedStock";
import { ForecastCard } from "./ForecastCard";
import { HeadlinesCard } from "./HeadlinesCard";
import { QuoteCard } from "./QuoteCard";
import { SentimentCard } from "./SentimentCard";
import { ExplainPanel } from "./ExplainPanel";
import { ErrorCard } from "./ui/ErrorCard";
import { Loading, Skeleton } from "./ui/Skeleton";

export function Dashboard() {
  const { selected } = useSelectedStock();
  const symbol = selected?.symbol ?? null;
  const stock = useApi(symbol && `stock:${symbol}`, () => getStock(symbol ?? ""));

  // The stock selector reports its own loading and error states.
  if (!symbol) return null;

  if (stock.status === "loading") {
    return (
      <Loading label={`Loading ${symbol}`}>
        <div className="flex flex-wrap gap-6">
          <Skeleton className="h-[380px] min-w-0 flex-[999_1_560px]" />
          <Skeleton className="h-[380px] min-w-0 flex-[1_1_280px]" />
        </div>
        <Skeleton className="h-[260px]" />
        <Skeleton className="h-[320px]" />
      </Loading>
    );
  }
  if (stock.status === "error") {
    return <ErrorCard what={symbol} error={stock.error} onRetry={stock.reload} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap gap-6">
        <QuoteCard stock={stock.data} />
        <ForecastCard symbol={stock.data.symbol} forecast={stock.data.forecast} />
      </div>
      <SentimentCard
        symbol={stock.data.symbol}
        sentiment={stock.data.sentiment}
        headlines={stock.data.headlines}
      />
      {stock.data.sentiment.gap && <ExplainPanel key={stock.data.symbol} symbol={stock.data.symbol} />}
      <HeadlinesCard headlines={stock.data.headlines} />
    </div>
  );
}
