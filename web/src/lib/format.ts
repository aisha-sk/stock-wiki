// The one place that turns contract units into display text.
// See docs/CONTRACT.md section 2 for the units.

import type { Label } from "./types";

const MINUS = "−";
export const EMPTY = "—";

const sign = (value: number) => (value > 0 ? "+" : value < 0 ? MINUS : "");

/** Sentiment score, integer -100 to 100: 42 -> "+42", -37 -> "−37". */
export const formatScore = (score: number) => `${sign(score)}${Math.abs(score)}`;

/** A 0 to 1 fraction as a percentage: 0.584 -> "58.4%". */
export const formatRate = (rate: number, digits = 1) => `${(rate * 100).toFixed(digits)}%`;

/** A 0 to 1 fraction that can be negative, signed: -0.087 -> "−8.7%". */
export const formatSignedRate = (rate: number, digits = 1) =>
  `${sign(rate)}${Math.abs(rate * 100).toFixed(digits)}%`;

/** A `_pct` value, already in percent units: 1.77 -> "+1.77%". */
export const formatPct = (pct: number, digits = 2) => `${sign(pct)}${Math.abs(pct).toFixed(digits)}%`;

export const formatPrice = (price: number) => price.toFixed(2);

/** Lowercase enum to display text: "bullish" -> "Bullish". */
export const capitalize = (value: string) => value.charAt(0).toUpperCase() + value.slice(1);

export const formatVersion = (version: string) => `v${version}`;

/** Tailwind text colour for a sentiment label. */
export const labelColor = (label: Label) =>
  label === "bullish" ? "text-bull" : label === "bearish" ? "text-bear" : "text-muted";

/** A `YYYY-MM-DD` session date. Formatted in UTC so it never shifts a day. */
export function formatDate(date: string, withYear = false) {
  return new Date(`${date}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: withYear ? "numeric" : undefined,
    timeZone: "UTC",
  });
}

/** A UTC timestamp, shown in the viewer's local time. */
export function formatDateTime(timestamp: string) {
  return new Date(timestamp).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
