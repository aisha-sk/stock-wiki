"use client";

import { usePathname, useRouter } from "next/navigation";
import { useSelectedStock } from "@/lib/useSelectedStock";

export function StockSelector() {
  const router = useRouter();
  const pathname = usePathname();
  const { tickers, selected } = useSelectedStock();

  if (tickers.status === "loading") {
    return <div className="h-11 w-72 animate-pulse rounded-full bg-line" aria-label="Loading stocks" />;
  }
  if (tickers.status === "error") {
    return (
      <div role="alert" className="flex flex-wrap items-center gap-3 text-[15px]">
        <span>Couldn&apos;t load the stock list. {tickers.error.message}</span>
        <button
          onClick={tickers.reload}
          className="min-h-11 rounded-lg border border-ink bg-card px-4 font-medium"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div role="group" aria-label="Choose a stock" className="flex flex-wrap items-center gap-2">
      <span className="mr-2 text-sm text-muted">Tracking</span>
      {tickers.data.tickers.map((ticker) => {
        const active = ticker.symbol === selected?.symbol;
        return (
          <button
            key={ticker.symbol}
            title={ticker.name}
            aria-pressed={active}
            onClick={() => router.replace(`${pathname}?symbol=${ticker.symbol}`, { scroll: false })}
            className={`min-h-11 rounded-full border px-5 text-[15px] font-medium ${
              active ? "border-ink bg-ink text-white" : "border-control bg-card text-ink hover:border-ink"
            }`}
          >
            {ticker.symbol}
          </button>
        );
      })}
    </div>
  );
}
