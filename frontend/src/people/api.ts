// The people API (U14): a profile by its handle, its cabinet (published slides and identifications), one's own export,
// the label stocks and the addresses of the label sheets (PDF, opened by the browser, which prints them at 100 %).
import { send } from "../api/client";
import type { PersonIdentificationRecord, ProfileRecord, SlidePage, StockRecord } from "../contract/catalog";

const person = (handle: string) => `/api/people/${encodeURIComponent(handle)}`;

export const PAGE = 48;

export const peopleApi = {
  profile: (handle: string, signal?: AbortSignal) =>
    send<ProfileRecord>("GET", person(handle), undefined, signal) as Promise<ProfileRecord>,
  slides: (handle: string, collection: string | null, offset: number, signal?: AbortSignal) => {
    const q = new URLSearchParams({ offset: String(offset), limit: String(PAGE) });
    if (collection) q.set("collection", collection);
    return send<SlidePage>("GET", `${person(handle)}/slides?${q}`, undefined, signal) as Promise<SlidePage>;
  },
  identifications: (handle: string, offset: number, signal?: AbortSignal) =>
    send<PersonIdentificationRecord[]>("GET", `${person(handle)}/identifications?offset=${offset}&limit=${PAGE}`,
      undefined, signal) as Promise<PersonIdentificationRecord[]>,
  stocks: (signal?: AbortSignal) =>
    send<StockRecord[]>("GET", "/api/labels/stocks", undefined, signal) as Promise<StockRecord[]>,
};

/** One's own slides as CSV, with their exact places (only the signed-in account reads it). */
export const EXPORT_URL = "/api/people/me/slides.csv";

export interface SheetRequest {
  stock: string;
  slides: string[];
  start: number;
  offset: Offset;
  lang: "en" | "es";
}

export interface Offset {
  dx: number;
  dy: number;
}

const mm = (v: number) => (Math.round(v * 10) / 10).toFixed(1);

/** The address of a sheet of labels for ``slides`` on ``stock``, from position ``start`` (0-based). */
export function sheetUrl({ stock, slides, start, offset, lang }: SheetRequest): string {
  const q = new URLSearchParams({ stock, slides: slides.join(","), start: String(start), dx: mm(offset.dx),
    dy: mm(offset.dy), lang });
  return `/api/labels/sheet.pdf?${q}`;
}

/** The address of a stock's test page: every label's outline, to hold against a sheet. */
export function testPageUrl(stock: string, offset: Offset): string {
  const q = new URLSearchParams({ stock, test: "true", dx: mm(offset.dx), dy: mm(offset.dy) });
  return `/api/labels/sheet.pdf?${q}`;
}
