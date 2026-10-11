"use client";

import { getHealth } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useApi } from "@/lib/useApi";

export function Footer() {
  const health = useApi("health", getHealth);
  const asOf = health.data?.data_generated_at;
  return (
    <footer className="pb-6 pt-6 text-[13px] text-muted">
      {asOf && (
        <p>
          Data as of {formatDateTime(asOf)}
          {health.data?.is_demo_data ? " (demo data, not real market data)" : ""}.
        </p>
      )}
      <p>
        SentiFi is for research and education. Nothing here is financial advice, and past forecasts do not
        guarantee future results.
      </p>
    </footer>
  );
}
