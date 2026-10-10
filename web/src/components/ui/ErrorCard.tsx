import type { ApiError } from "@/lib/api";

/** A failed request, with a way to try again. `what` finishes "Couldn't load …". */
export function ErrorCard({
  what,
  error,
  onRetry,
  bare = false,
}: {
  what: string;
  error: ApiError;
  onRetry: () => void;
  /** Render without the card frame, for use inside another card. */
  bare?: boolean;
}) {
  const unreachable = error.code === "network_error";
  return (
    <div
      role="alert"
      className={`flex flex-wrap items-center justify-between gap-x-6 gap-y-3 ${
        bare ? "" : "rounded-xl border border-line bg-card p-6"
      }`}
    >
      <div className="min-w-0">
        <div className="font-semibold">
          {unreachable ? "Can't reach the SentiFi API" : `Couldn't load ${what}`}
        </div>
        <div className="text-[15px] text-muted">
          {unreachable ? "It may be starting up or offline." : error.message}
        </div>
      </div>
      <button onClick={onRetry} className="min-h-11 rounded-lg border border-ink bg-card px-4 font-medium">
        Retry
      </button>
    </div>
  );
}
