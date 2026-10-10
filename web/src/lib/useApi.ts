"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "./api";

export type ApiState<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "ready"; data: T; error: null }
  | { status: "error"; data: null; error: ApiError };

const LOADING = { status: "loading", data: null, error: null } as const;

// One in-flight or settled request per key, shared by every component that asks for it.
const cache = new Map<string, Promise<unknown>>();

/**
 * Fetch on mount and whenever `key` changes. Pass `null` as the key to wait.
 * `reload` drops the cached result and fetches again.
 */
export function useApi<T>(key: string | null, fetcher: () => Promise<T>) {
  const [settled, setSettled] = useState<{ key: string; state: ApiState<T> } | null>(null);
  const [attempt, setAttempt] = useState(0);

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
        if (active) setSettled({ key, state: { status: "ready", data, error: null } });
      },
      (cause: unknown) => {
        cache.delete(key);
        const error =
          cause instanceof ApiError ? cause : new ApiError(0, "internal_error", "Something went wrong.");
        if (active) setSettled({ key, state: { status: "error", data: null, error } });
      },
    );
    return () => {
      active = false;
    };
    // `fetcher` is identified by `key`; callers pass a fresh closure each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, attempt]);

  const reload = useCallback(() => {
    if (key !== null) cache.delete(key);
    setSettled(null);
    setAttempt((n) => n + 1);
  }, [key]);

  const state: ApiState<T> = settled && settled.key === key ? settled.state : LOADING;
  return { ...state, reload };
}
