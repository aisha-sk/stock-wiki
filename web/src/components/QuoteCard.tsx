import { formatDate, formatPct, formatPrice } from "@/lib/format";
import type { Stock } from "@/lib/types";
import { PriceChart, SESSIONS_SHOWN } from "./PriceChart";

export function QuoteCard({ stock }: { stock: Stock }) {
  const { quote } = stock;
  const sessions = Math.min(SESSIONS_SHOWN, stock.prices.length);
  return (
    <section
      aria-label={`${stock.symbol} price`}
      className="flex min-w-0 flex-[999_1_560px] flex-col gap-4 rounded-xl border border-line bg-card p-6"
    >
      <div className="flex flex-wrap justify-between gap-3">
        <div>
          <h1 className="text-sm font-normal text-muted">
            {stock.symbol} · {stock.name}
          </h1>
          <div className="flex flex-wrap items-baseline gap-x-3">
            <span className="font-mono text-[40px] font-medium leading-tight">{formatPrice(quote.price)}</span>
            <span className={`font-mono text-base ${quote.change_pct >= 0 ? "text-bull" : "text-bear"}`}>
              {formatPct(quote.change_pct)}
            </span>
            <span className="text-[13px] text-muted">as of {formatDate(quote.as_of)}</span>
          </div>
        </div>
        <p className="text-[13px] text-muted">
          Price, last {sessions} sessions
        </p>
      </div>
      <PriceChart symbol={stock.symbol} prices={stock.prices} />
    </section>
  );
}
