"use client";

import { useState } from "react";
import { ApiError, explain } from "@/lib/api";
import type { Explanation } from "@/lib/types";

type State =
  | { status: "idle" }
  | { status: "asking" }
  | { status: "answered"; explanation: Explanation }
  | { status: "unavailable"; message: string };

/** Asks the explain agent why the groups disagree, and shows its answer with the headlines it cites. */
export function ExplainPanel({ symbol }: { symbol: string }) {
  const [state, setState] = useState<State>({ status: "idle" });

  async function ask() {
    setState({ status: "asking" });
    try {
      const explanation = await explain(symbol, `Why do these groups feel differently about ${symbol}?`);
      setState({ status: "answered", explanation });
    } catch (cause) {
      const message =
        cause instanceof ApiError && cause.code !== "network_error"
          ? cause.message
          : "Can't reach the SentiFi API.";
      setState({ status: "unavailable", message });
    }
  }

  return (
    <section aria-labelledby="explain-title" className="rounded-xl border border-line bg-card p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="explain-title" className="font-display text-2xl font-medium">
            Why do they disagree?
          </h2>
          <p className="text-sm text-muted">
            An AI reads the scores and headlines above and answers, citing the headlines it used.
          </p>
        </div>
        {state.status !== "answered" && state.status !== "unavailable" && (
          <button
            onClick={ask}
            disabled={state.status === "asking"}
            className="min-h-11 rounded-lg bg-ink px-4 text-[15px] font-medium text-white disabled:opacity-60"
          >
            {state.status === "asking" ? "Reading the headlines…" : "Ask"}
          </button>
        )}
      </div>

      {state.status === "unavailable" && (
        <p role="status" className="mt-4 text-[15px] text-muted">
          {state.message}
        </p>
      )}

      {state.status === "answered" && (
        <div className="mt-4 border-t border-line pt-4">
          <p className="max-w-[75ch] text-base leading-relaxed">{state.explanation.answer}</p>
          <ul className="mt-4 flex flex-col gap-2">
            {state.explanation.citations.map((citation) => (
              <li key={citation.headline_id} className="text-sm">
                <span aria-hidden="true" className="mr-2 text-muted">
                  ↳
                </span>
                {citation.url ? (
                  <a
                    href={citation.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline decoration-line underline-offset-4 hover:decoration-ink"
                  >
                    {citation.title}
                  </a>
                ) : (
                  citation.title
                )}
              </li>
            ))}
          </ul>
          <p className="mt-4 text-[13px] text-muted">
            AI-generated summary ({state.explanation.model}), limited to the headlines on this page. Not
            financial advice.
          </p>
        </div>
      )}
    </section>
  );
}
