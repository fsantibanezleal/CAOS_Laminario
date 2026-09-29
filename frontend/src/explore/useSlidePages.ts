// The slides of a filtered place, page by page: the first ``shown / PAGE`` pages of 48, each fetched once and kept,
// so "show more" fetches only the next page and going back redraws every page the visitor had opened.
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { SlideSummary } from "../contract/catalog";
import { PAGE } from "./filters";

const pages = new Map<string, { items: SlideSummary[]; total: number }>();

export interface SlidePages {
  items: SlideSummary[];
  total: number | null;
  loading: boolean;
  error: Error | null;
  retry: () => void;
}

export function useSlidePages(query: URLSearchParams, shown: number): SlidePages {
  const base = query.toString();
  const count = Math.max(1, Math.round(shown / PAGE));
  const keys = Array.from({ length: count }, (_, i) => `${base}#${i}`);
  const complete = keys.every((k) => pages.has(k));
  const [, redraw] = useState(0);
  const [error, setError] = useState<Error | null>(null);
  const [attempt, setAttempt] = useState(0);
  const last = useRef<{ items: SlideSummary[]; total: number | null }>({ items: [], total: null });

  useEffect(() => {
    if (complete) return undefined;
    const controller = new AbortController();
    setError(null);
    const missing = keys.map((k, i) => [k, i] as const).filter(([k]) => !pages.has(k));
    Promise.all(missing.map(([key, i]) => {
      const q = new URLSearchParams(base);
      q.set("offset", String(i * PAGE));
      q.set("limit", String(PAGE));
      return api.slides(q, controller.signal).then((page) => pages.set(key, { items: page.items, total: page.total }));
    })).then(
      () => { if (!controller.signal.aborted) redraw((n) => n + 1); },
      (e: Error) => { if (!controller.signal.aborted) setError(e); },
    );
    return () => controller.abort();
    // The keys are derived from base and count.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [base, count, complete, attempt]);

  if (complete) {
    const loaded = keys.map((k) => pages.get(k)!);
    last.current = { items: loaded.flatMap((p) => p.items), total: loaded[0].total };
    return { ...last.current, loading: false, error: null, retry: () => undefined };
  }
  // While a new state loads, the pages already drawn stay (the tray does not blank); a new first page replaces them.
  const opened = keys.filter((k) => pages.has(k)).map((k) => pages.get(k)!);
  const partial = opened.length && pages.has(keys[0])
    ? { items: opened.flatMap((p) => p.items), total: opened[0].total }
    : last.current;
  return { ...partial, loading: true, error, retry: () => setAttempt((n) => n + 1) };
}
