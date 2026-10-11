"use client";

import { useState } from "react";
import { ApiError, createAlert, getAlertPreview } from "@/lib/api";
import type { AlertResponse, AlertTrigger } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { useSelectedStock } from "@/lib/useSelectedStock";
import { ErrorCard } from "./ui/ErrorCard";
import { Skeleton } from "./ui/Skeleton";

const TRIGGERS: { value: AlertTrigger; label: string }[] = [
  { value: "sharp_shift", label: "Sentiment shifts sharply" },
  { value: "any_flip", label: "Any bull/bear flip" },
  { value: "weekly_digest", label: "Weekly digest only" },
];

type Submission =
  | { status: "idle" }
  | { status: "sending" }
  | { status: "done"; alert: AlertResponse }
  | { status: "failed"; error: ApiError };

function SignUpForm({ symbol }: { symbol: string }) {
  const [email, setEmail] = useState("");
  const [trigger, setTrigger] = useState<AlertTrigger>("sharp_shift");
  const [submission, setSubmission] = useState<Submission>({ status: "idle" });

  // A confirmation or error belongs to the stock and choices it was made for.
  const [shownFor, setShownFor] = useState(symbol);
  if (shownFor !== symbol) {
    setShownFor(symbol);
    setSubmission({ status: "idle" });
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSubmission({ status: "sending" });
    try {
      setSubmission({ status: "done", alert: await createAlert({ email, symbol, trigger }) });
    } catch (cause) {
      const error = cause instanceof ApiError ? cause : new ApiError(0, "internal_error", "Something went wrong.");
      setSubmission({ status: "failed", error });
    }
  }

  const invalid = submission.status === "failed" && submission.error.code === "validation_error";
  const otherFailure = submission.status === "failed" && !invalid ? submission.error : null;

  return (
    <form
      onSubmit={submit}
      noValidate
      className="flex min-w-0 flex-[1_1_420px] flex-col gap-5 rounded-xl border border-line bg-card p-8"
    >
      <div>
        <h1 className="mb-2 font-display text-3xl font-medium">Get a Sentiment Alert</h1>
        <p className="text-[15px] text-muted">
          We email you when the story around a stock changes. Free, no card.
        </p>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="alert-email" className="text-sm font-medium">
          Email
        </label>
        <input
          id="alert-email"
          type="email"
          name="email"
          autoComplete="email"
          placeholder="you@example.com"
          required
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
            setSubmission({ status: "idle" });
          }}
          aria-invalid={invalid}
          aria-describedby={invalid ? "alert-email-error" : undefined}
          className={`min-h-11 rounded-lg border bg-card px-3.5 text-base ${invalid ? "border-bear" : "border-control"}`}
        />
        {invalid && (
          <p id="alert-email-error" role="alert" className="text-sm text-bear">
            Enter a valid email address.
          </p>
        )}
      </div>

      <div role="group" aria-label="Alert type" className="flex flex-col gap-2">
        <div className="text-sm font-medium">
          Alert me on <span className="font-mono">{symbol}</span> when
        </div>
        <div className="flex flex-wrap gap-2">
          {TRIGGERS.map((option) => {
            const active = option.value === trigger;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={active}
                onClick={() => {
                  setTrigger(option.value);
                  setSubmission({ status: "idle" });
                }}
                className={`min-h-11 rounded-full border px-5 text-[15px] font-medium ${
                  active ? "border-ink bg-ink text-white" : "border-control bg-card text-ink hover:border-ink"
                }`}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>

      <button
        type="submit"
        disabled={submission.status === "sending"}
        className="min-h-12 rounded-lg bg-ink text-base font-medium text-white disabled:opacity-60"
      >
        {submission.status === "sending" ? "Creating…" : "Create alert"}
      </button>

      {submission.status === "done" && (
        <p role="status" className="rounded-lg border border-bull px-4 py-3 text-[15px] font-medium text-bull">
          Alert created for {submission.alert.symbol}. This is a demo: sign-ups are stored, and no email is
          sent yet.
        </p>
      )}
      {otherFailure && (
        <p role="alert" className="rounded-lg border border-bear px-4 py-3 text-[15px] text-bear">
          {otherFailure.code === "network_error"
            ? "Can't reach the SentiFi API. Your alert was not created."
            : `Your alert was not created. ${otherFailure.message}`}
        </p>
      )}
    </form>
  );
}

function ExampleEmail({ symbol }: { symbol: string }) {
  const preview = useApi(`alert-preview:${symbol}`, () => getAlertPreview(symbol));
  return (
    <section
      aria-label="Example email"
      className="flex min-w-0 flex-[1_1_360px] flex-col gap-3 rounded-xl border border-line bg-card p-6"
    >
      <div className="text-[13px] text-muted">Example email, built from today&apos;s {symbol} data</div>
      {preview.status === "loading" && <Skeleton className="h-[120px]" />}
      {preview.status === "error" && (
        <ErrorCard bare what="the example email" error={preview.error} onRetry={preview.reload} />
      )}
      {preview.status === "ready" && (
        <>
          <h2 className="text-[17px] font-semibold">{preview.data.subject}</h2>
          {preview.data.body_lines.map((line) => (
            <p key={line} className="text-[15px] leading-relaxed">
              {line}
            </p>
          ))}
          <p className="border-t border-line pt-3 text-[13px] text-muted">
            {preview.data.is_demo_data ? "Demo data. " : ""}Not financial advice.
          </p>
        </>
      )}
    </section>
  );
}

export function Alerts() {
  const { selected } = useSelectedStock();
  // The stock selector reports its own loading and error states.
  if (!selected) return null;
  return (
    <div className="flex flex-wrap items-start gap-6">
      <SignUpForm symbol={selected.symbol} />
      <ExampleEmail symbol={selected.symbol} />
    </div>
  );
}
