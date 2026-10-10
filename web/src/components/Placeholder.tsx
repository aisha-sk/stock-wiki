"use client";

import { useSelectedStock } from "@/lib/useSelectedStock";

/** Stand-in for a tab whose cards land in a later ticket. */
export function Placeholder({ title, ticket }: { title: string; ticket: string }) {
  const { selected } = useSelectedStock();
  return (
    <section className="rounded-xl border border-line bg-card p-6">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="mt-1 text-[15px] text-muted">
        {selected ? `${selected.symbol} · ${selected.name} — ` : ""}
        this tab is built in ticket {ticket}.
      </p>
    </section>
  );
}
