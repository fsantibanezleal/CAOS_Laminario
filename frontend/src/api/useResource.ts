// A value fetched for a place: loading, then the value or the error. Answers are kept by key for the life of the
// page (the tree, the vocabularies and the pages a visitor has seen), so going back draws at once; a key that
// changes aborts the request it replaces.
import { useEffect, useState } from "react";

const cache = new Map<string, unknown>();
const MAX_ENTRIES = 200;

export type Resource<T> =
  | { state: "loading"; value?: T }
  | { state: "ready"; value: T }
  | { state: "error"; error: Error; value?: T };

function remember(key: string, value: unknown): void {
  cache.delete(key);
  cache.set(key, value);
  if (cache.size > MAX_ENTRIES) cache.delete(cache.keys().next().value as string);
}

/** Fetch ``load`` under ``key``; while a new key loads, the previous value stays (so a list does not blank). */
export function useResource<T>(key: string | null, load: (signal: AbortSignal) => Promise<T>): Resource<T> {
  const [resource, setResource] = useState<Resource<T>>(() =>
    key !== null && cache.has(key) ? { state: "ready", value: cache.get(key) as T } : { state: "loading" });

  useEffect(() => {
    if (key === null) return undefined;
    if (cache.has(key)) {
      setResource({ state: "ready", value: cache.get(key) as T });
      return undefined;
    }
    const controller = new AbortController();
    setResource((previous) => ({ state: "loading", value: previous.value }));
    load(controller.signal).then(
      (value) => {
        remember(key, value);
        if (!controller.signal.aborted) setResource({ state: "ready", value });
      },
      (error: Error) => {
        if (!controller.signal.aborted) setResource((previous) => ({ state: "error", error, value: previous.value }));
      },
    );
    return () => controller.abort();
    // `load` is a fresh closure on every render; the key names what it fetches.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return resource;
}
