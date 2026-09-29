// The filters of the Explore places, read from and written to the address, so every state of a drawer, a search or
// the map can be shared and reopened (R-1006). The parameter names are the API's: a place hands its query string
// to /api/slides, /api/explore/facets and /api/explore/map as it is, adding only its own node.

export const FACETS = ["kind", "preparation", "modality", "preservation", "country", "licence", "wsi", "origin"] as const;
export type Facet = (typeof FACETS)[number];

export const SORTS = ["newest", "name", "relevance"] as const;
export type Sort = (typeof SORTS)[number];

export const PAGE = 48;

export interface Filters {
  node?: string;
  q: string;
  values: Record<Facet, string[]>;
  sort?: Sort;
  /** How many slides the visitor asked to see (a multiple of PAGE). */
  shown: number;
}

export function readFilters(params: URLSearchParams): Filters {
  const values = Object.fromEntries(FACETS.map((f) => [f, [...new Set(params.getAll(f).filter(Boolean))]])) as
    Record<Facet, string[]>;
  const sort = params.get("sort");
  const shown = Number.parseInt(params.get("n") ?? "", 10);
  return {
    node: params.get("node") ?? undefined,
    q: params.get("q") ?? "",
    values,
    sort: (SORTS as readonly string[]).includes(sort ?? "") ? (sort as Sort) : undefined,
    shown: Number.isFinite(shown) && shown > PAGE ? Math.ceil(shown / PAGE) * PAGE : PAGE,
  };
}

/** The address's query string for a state of the filters (empty values left out, facets in a stable order). */
export function writeFilters(f: Filters): URLSearchParams {
  const out = new URLSearchParams();
  if (f.node) out.set("node", f.node);
  if (f.q.trim()) out.set("q", f.q.trim());
  for (const facet of FACETS) for (const v of f.values[facet]) out.append(facet, v);
  if (f.sort) out.set("sort", f.sort);
  if (f.shown > PAGE) out.set("n", String(f.shown));
  return out;
}

/** The sort in force: the visitor's, else relevance while there are words, else newest. */
export function sortOf(f: Filters): Sort {
  if (f.sort && (f.sort !== "relevance" || f.q.trim())) return f.sort;
  return f.q.trim() ? "relevance" : "newest";
}

/** The query the API reads: the filters, with the place's own node when it has one (a drawer). */
export function apiQuery(f: Filters, extra: Record<string, string> = {}, node?: string): URLSearchParams {
  const out = new URLSearchParams();
  const scope = node ?? f.node;
  if (scope) out.set("node", scope);
  if (f.q.trim()) out.set("q", f.q.trim());
  for (const facet of FACETS) {
    if (facet === "wsi") {
      // Whole-slide is a yes-or-no filter: one value applies, both cancel out.
      if (f.values.wsi.length === 1) out.set("wsi", f.values.wsi[0] === "yes" ? "true" : "false");
      continue;
    }
    for (const v of f.values[facet]) out.append(facet, v);
  }
  for (const [k, v] of Object.entries(extra)) out.set(k, v);
  return out;
}

export function activeCount(f: Filters): number {
  return FACETS.reduce((n, facet) => n + f.values[facet].length, 0);
}

export function toggle(f: Filters, facet: Facet, value: string, on: boolean): Filters {
  const current = f.values[facet].filter((v) => v !== value);
  return { ...f, values: { ...f.values, [facet]: on ? [...current, value] : current }, shown: PAGE };
}

export function cleared(f: Filters): Filters {
  const none = Object.fromEntries(FACETS.map((k) => [k, [] as string[]])) as Record<Facet, string[]>;
  return { ...f, values: none, shown: PAGE };
}
