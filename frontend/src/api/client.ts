// The API, typed by the generated contract. Every call takes an AbortSignal, so a place that is left, or a query
// that is replaced while the visitor types, stops its request instead of drawing a stale answer.
import type {
  AccountRecord,
  AnnotationRecord,
  CollectionTreeRecord,
  FacetCounts,
  FacetRecord,
  MapRecord,
  PartRecord,
  SlidePage,
  SlideRecord,
} from "../contract/catalog";

export class ApiError extends Error {
  /** The answer's body, when it was JSON: FastAPI's {detail}, or a validation result. */
  constructor(public status: number, public url: string, public body: unknown = null) {
    super(`${status} from ${url}`);
  }

  /** The refusal's code (fastapi-users' {detail: "CODE"} or {detail: {code, reason}}), if it has one. */
  get code(): string | null {
    const detail = (this.body as { detail?: unknown } | null)?.detail;
    if (typeof detail === "string" && /^[A-Z][A-Z_]+$/.test(detail)) return detail;
    if (detail && typeof detail === "object" && typeof (detail as { code?: unknown }).code === "string") {
      return (detail as { code: string }).code;
    }
    return null;
  }

  /** The server's own words (English), for a refusal the interface has no words of its own for. */
  get reason(): string | null {
    const detail = (this.body as { detail?: unknown } | null)?.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && typeof (detail as { reason?: unknown }).reason === "string") {
      return (detail as { reason: string }).reason;
    }
    return null;
  }
}

async function failure(response: Response, url: string): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // not JSON (a proxy's page, an empty answer)
  }
  return new ApiError(response.status, url, body);
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw await failure(response, url);
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

export async function send<T>(method: string, url: string, body?: unknown, signal?: AbortSignal): Promise<T | null> {
  const form = body instanceof URLSearchParams;
  const response = await fetch(url, {
    method, signal,
    headers: body === undefined ? { Accept: "application/json" }
      : { "Content-Type": form ? "application/x-www-form-urlencoded" : "application/json", Accept: "application/json" },
    body: body === undefined ? undefined : form ? body : JSON.stringify(body),
  });
  if (!response.ok) throw await failure(response, url);
  if (response.status === 204 || response.status === 202) return null;
  const text = await response.text();
  return text ? (JSON.parse(text) as T) : null;
}

const slidePath = (id: string) => `/api/slides/${encodeURIComponent(id)}`;

export const api = {
  tree: (signal?: AbortSignal) => getJson<CollectionTreeRecord>("/api/collections", signal),
  facetNames: (signal?: AbortSignal) => getJson<FacetRecord[]>("/api/facets", signal),
  countryNames: (signal?: AbortSignal) => getJson<CountryNames>("/api/explore/country-names", signal),
  countryShapes: (signal?: AbortSignal) => getJson<CountryShapes>("/api/explore/countries", signal),
  slides: (query: URLSearchParams, signal?: AbortSignal) => getJson<SlidePage>(`/api/slides?${query}`, signal),
  facets: (query: URLSearchParams, signal?: AbortSignal) =>
    getJson<FacetCounts>(`/api/explore/facets?${query}`, signal),
  map: (query: URLSearchParams, signal?: AbortSignal) => getJson<MapRecord>(`/api/explore/map?${query}`, signal),
  slide: (id: string, signal?: AbortSignal) => getJson<SlideRecord>(slidePath(id), signal),
  /** The slide drawn by the server, to inline: its colours come from the page (standalone=false). */
  slideSvg: async (id: string, lang: string, signal?: AbortSignal) => {
    const url = `${slidePath(id)}/slide.svg?standalone=false&lang=${lang}`;
    const response = await fetch(url, { signal });
    if (!response.ok) throw new ApiError(response.status, url);
    return response.text();
  },
  annotations: (slide: string, asset: number, signal?: AbortSignal) =>
    getJson<AnnotationRecord[]>(`${slidePath(slide)}/assets/${asset}/annotations`, signal),
  addAnnotation: (slide: string, asset: number, annotation: unknown) =>
    send<AnnotationRecord>("POST", `${slidePath(slide)}/assets/${asset}/annotations`, annotation),
  removeAnnotation: (id: string) => send<null>("DELETE", `/api/annotations/${encodeURIComponent(id)}`),
  parts: (signal?: AbortSignal) => getJson<PartRecord[]>("/api/vocab/parts", signal),
  /** The signed-in account, or null for a visitor. */
  me: (signal?: AbortSignal) => getJson<AccountRecord | null>("/api/session", signal),
};

export const labelPdf = (id: string, lang: string) => `${slidePath(id)}/label.pdf?lang=${lang}`;
export const slideDrawing = (id: string, lang: string) => `${slidePath(id)}/slide.svg?standalone=true&lang=${lang}`;

export const BASEMAP_URL = "/api/explore/basemap.pmtiles";
