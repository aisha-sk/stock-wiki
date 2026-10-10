"use client";

import { useSearchParams } from "next/navigation";
import { getTickers } from "./api";
import { useApi } from "./useApi";

/**
 * The stock chosen with `?symbol=`. Falls back to the first ticker when the
 * parameter is missing or unknown. Must render inside a Suspense boundary.
 */
export function useSelectedStock() {
  const requested = useSearchParams().get("symbol")?.toUpperCase() ?? null;
  const tickers = useApi("tickers", getTickers);
  const list = tickers.data?.tickers ?? [];
  const selected = list.find((t) => t.symbol === requested) ?? list[0] ?? null;
  return {
    tickers,
    selected,
    /** The raw `?symbol=` value, upper-cased, or null. */
    requested,
    /** True when `?symbol=` named a stock we do not track. */
    isFallback: requested !== null && selected !== null && selected.symbol !== requested,
  };
}
