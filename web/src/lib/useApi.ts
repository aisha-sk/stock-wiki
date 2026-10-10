"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { ApiError } from "./api";

export type ApiState<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "ready"; data: T; error: null }
  | { status: "error"; data: null; error: ApiError };

const LOADING = { status: "loading", data: null, error: null } as const;

// One in-flight or settled request per key, shared by every component that asks for it.
// Failed requests are dropped, so the next attempt goes back to the network.
const cache = new Map<string, Promise<unknown>>();

// Bumped by every `reload`. Each hook re-runs when it changes: successful requests come
// straight back from the cache, failed ones are fetched again. One Retry click therefore
// recovers the whole page, not only the card it sits in.
let retryRound = 0;
const listeners = new Set<() => void>();
const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => void listeners.delete(listener);
};

/**
 * Fetch on mount and whenever `key` changes. Pass `null` as the key to wait.
 * `reload` drops this key's cached result and fetches again.
 */
export function useApi<T>(key: string | null, fetcher: () => Promise<T>) {
  const [settled, setSettled] = useState<{ key: string; round: number; state: ApiState<T> } | null>(null);
  const round = useSyncExternalStore(
    subscribe,
    () => retryRound,
    () => 0,
  );

  useEffect(() => {
    if (key === null) return;
    let active = true;
    let promise = cache.get(key) as Promise<T> | undefined;
    if (!promise) {
      promise = fetcher();
      cache.set(key, promise);
    }
    promise.then(
      (data) => {
        if (active) setSettled({ key, round, state: { status: "ready", data, error: null } });
      },
      (cause: unknown) => {
        cache.delete(key);
        const error =
          cause instanceof ApiError ? cause : new ApiError(0, "internal_error", "Something went wrong.");
        if (active) setSettled({ key, round, state: { status: "error", data: null, error } });
      },
    );
    return () => {
      active = false;
    };
    // `fetcher` is identified by `key`; callers pass a fresh closure each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, round]);

  const reload = useCallback(() => {
    if (key !== null) cache.delete(key);
    retryRound += 1;
    listeners.forEach((listener) => listener());
  }, [key]);

  if (!settled || settled.key !== key) return { ...LOADING, reload };
  // An error from an earlier round is being retried; anything else stays on screen meanwhile.
  if (settled.state.status === "error" && settled.round !== round) return { ...LOADING, reload };
  return { ...settled.state, reload };
}
