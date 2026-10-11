"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { getHealth } from "@/lib/api";
import { useApi } from "@/lib/useApi";

const TABS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/model", label: "Model performance" },
  { href: "/alerts", label: "Alerts" },
];

export function Header() {
  const pathname = usePathname();
  const symbol = useSearchParams().get("symbol");
  const health = useApi("health", getHealth);
  // Keep the chosen stock when moving between tabs.
  const withSymbol = (href: string) => (symbol ? `${href}?symbol=${encodeURIComponent(symbol)}` : href);

  return (
    <header className="border-b border-line bg-card">
      <div className="mx-auto flex max-w-[1200px] flex-wrap items-center gap-x-8 gap-y-4 px-6 py-3">
        <Link href={withSymbol("/")} className="flex items-center gap-2.5 text-xl font-semibold">
          <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
            <rect width="28" height="28" rx="6" className="fill-ink" />
            <path
              d="M6 19 L11 13 L15 16 L22 8"
              fill="none"
              stroke="#fff"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          StockSense
        </Link>

        <nav aria-label="Main" className="order-last flex basis-full gap-1 overflow-x-auto md:order-none md:flex-1 md:basis-auto">
          {TABS.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={withSymbol(tab.href)}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-11 shrink-0 items-center border-b-[3px] px-2.5 text-[15px] md:px-4 ${
                  active ? "border-ink font-semibold text-ink" : "border-transparent text-muted hover:text-ink"
                }`}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          {health.data?.is_demo_data && (
            <span className="rounded-full border border-control px-3 py-1 text-[13px] text-muted">Demo data</span>
          )}
          <Link
            href={withSymbol("/alerts")}
            className="flex min-h-11 items-center rounded-lg bg-ink px-5 text-[15px] font-medium text-white"
          >
            Get alerts
          </Link>
        </div>
      </div>
    </header>
  );
}
