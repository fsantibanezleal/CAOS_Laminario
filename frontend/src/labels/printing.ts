// What the print dialog keeps on the device (U14): the last stock chosen, and each stock's printer offset, which
// belongs to the printer, not to the account (dossier 16, section 2.3). The browser's storage may be missing (a private
// window, blocked site data): then nothing is kept and the defaults hold.
import type { Offset } from "../people/api";

const STOCK_KEY = "laminario.labels.stock";
const offsetKey = (stock: string) => `laminario.labels.offset.${stock}`;

/** The printer offset's bounds and step, in millimetres (the API accepts -10 to 10). */
export const OFFSET_LIMIT = 10;
export const OFFSET_STEP = 0.1;

export function clampOffset(value: number): number {
  if (!Number.isFinite(value)) return 0;
  const bounded = Math.min(OFFSET_LIMIT, Math.max(-OFFSET_LIMIT, value));
  return Math.round(bounded * 10) / 10;
}

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // not kept: the dialog still works with what is on the page
  }
}

export function savedStock(ids: string[], fallback: string): string {
  const saved = read(STOCK_KEY);
  return saved && ids.includes(saved) ? saved : fallback;
}

export function saveStock(id: string): void {
  write(STOCK_KEY, id);
}

export function savedOffset(stock: string): Offset {
  const raw = read(offsetKey(stock));
  if (!raw) return { dx: 0, dy: 0 };
  try {
    const value = JSON.parse(raw) as Partial<Offset>;
    return { dx: clampOffset(Number(value.dx ?? 0)), dy: clampOffset(Number(value.dy ?? 0)) };
  } catch {
    return { dx: 0, dy: 0 };
  }
}

export function saveOffset(stock: string, offset: Offset): void {
  write(offsetKey(stock), JSON.stringify({ dx: clampOffset(offset.dx), dy: clampOffset(offset.dy) }));
}

/** How many pages ``count`` labels fill from position ``start`` of a stock with ``perSheet`` labels. */
export function pagesFor(count: number, start: number, perSheet: number): number {
  if (count <= 0) return 0;
  return Math.ceil((start + count) / perSheet);
}
