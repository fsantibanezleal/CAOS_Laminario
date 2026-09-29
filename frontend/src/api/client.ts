// The API, typed by the generated contract. Every call takes an AbortSignal, so a place that is left, or a query
// that is replaced while the visitor types, stops its request instead of drawing a stale answer.
import type {
  CollectionTreeRecord,
  FacetCounts,
  FacetRecord,
  MapRecord,
  SlidePage,
} from "../contract/catalog";

export class ApiError extends Error {
  constructor(public status: number, public url: string) {
    super(`${status} from ${url}`);
  }
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new ApiError(response.status, url);
  return (await response.json()) as T;
}

export interface CountryNames {
  countries: Record<string, { en: string; es: string }>;
}

/** Country shapes: one feature per ISO code, with Natural Earth's label point and the zoom it is labelled from. */
export interface CountryShapes {
  type: "FeatureCollection";
  features: {
    type: "Feature";
    id: string;
    properties: { code: string; label: [number, number]; label_zoom: number };
    geometry: { type: "MultiPolygon"; coordinates: number[][][][] };
  }[];
}

export const api = {
  tree: (signal?: AbortSignal) => getJson<CollectionTreeRecord>("/api/collections", signal),
  facetNames: (signal?: AbortSignal) => getJson<FacetRecord[]>("/api/facets", signal),
  countryNames: (signal?: AbortSignal) => getJson<CountryNames>("/api/explore/country-names", signal),
  countryShapes: (signal?: AbortSignal) => getJson<CountryShapes>("/api/explore/countries", signal),
  slides: (query: URLSearchParams, signal?: AbortSignal) => getJson<SlidePage>(`/api/slides?${query}`, signal),
  facets: (query: URLSearchParams, signal?: AbortSignal) =>
    getJson<FacetCounts>(`/api/explore/facets?${query}`, signal),
  map: (query: URLSearchParams, signal?: AbortSignal) => getJson<MapRecord>(`/api/explore/map?${query}`, signal),
};

export const BASEMAP_URL = "/api/explore/basemap.pmtiles";
