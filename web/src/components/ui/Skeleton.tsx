/** A pulsing placeholder block. Size it with `className`. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-xl bg-line ${className}`} />;
}

/** Wraps skeleton blocks so screen readers hear one "Loading" message. */
export function Loading({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div role="status" aria-label={label} className="flex flex-col gap-6">
      {children}
    </div>
  );
}
