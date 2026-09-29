// The collection tree, fetched once for the page: the realms, cabinets and drawers are all drawn from it. It also
// holds the vocabularies the filters name their values with (preparations and modalities with their icons,
// countries in both languages).
import { createContext, useContext, useMemo, type ReactNode } from "react";
import { api, type CountryNames } from "../api/client";
import { useResource } from "../api/useResource";
import type { CollectionNodeRecord, FacetRecord, LocalisedText } from "../contract/catalog";

export interface TreeIndex {
  realms: CollectionNodeRecord[];
  byId: Map<string, CollectionNodeRecord>;
  parentOf: Map<string, string>;
  facets: Map<string, FacetRecord>;
  countries: CountryNames["countries"];
}

export type TreeState = { state: "loading" } | { state: "error"; error: Error } | { state: "ready"; tree: TreeIndex };

const Context = createContext<TreeState>({ state: "loading" });

function index(realms: CollectionNodeRecord[], facets: FacetRecord[], countries: CountryNames): TreeIndex {
  const byId = new Map<string, CollectionNodeRecord>();
  const parentOf = new Map<string, string>();
  const walk = (node: CollectionNodeRecord, parent?: string) => {
    byId.set(node.id, node);
    if (parent) parentOf.set(node.id, parent);
    for (const child of node.children ?? []) walk(child, node.id);
  };
  for (const realm of realms) walk(realm);
  return { realms, byId, parentOf, facets: new Map(facets.map((f) => [f.id, f])), countries: countries.countries };
}

export function TreeProvider({ children }: { children: ReactNode }) {
  const tree = useResource("tree", (signal) => api.tree(signal));
  const facets = useResource("facet-names", (signal) => api.facetNames(signal));
  const countries = useResource("country-names", (signal) => api.countryNames(signal));

  const state = useMemo<TreeState>(() => {
    for (const r of [tree, facets, countries]) if (r.state === "error") return { state: "error", error: r.error };
    if (tree.state === "ready" && facets.state === "ready" && countries.state === "ready") {
      return { state: "ready", tree: index(tree.value.realms, facets.value, countries.value) };
    }
    return { state: "loading" };
  }, [tree, facets, countries]);

  return <Context.Provider value={state}>{children}</Context.Provider>;
}

export function useTree(): TreeState {
  return useContext(Context);
}

/** The collection a node belongs to ("life.insects" for "life.insects.lice"); none for a realm. */
export function collectionOf(id: string): string | null {
  const parts = id.split(".");
  return parts.length >= 2 ? parts.slice(0, 2).join(".") : null;
}

/** The address of a node: a realm is the landing place, a collection its cabinet, anything deeper a drawer. */
export function nodeHref(id: string): string {
  const parts = id.split(".");
  if (parts.length === 1) return `/#${parts[0]}`;
  return `/c/${parts.slice(1).join("/")}`;
}

/** The node an address names (``["insects", "lice"]`` to "life.insects.lice"), or null. */
export function nodeFromPath(tree: TreeIndex, segments: string[]): CollectionNodeRecord | null {
  if (segments.length === 0) return null;
  const collection = tree.realms.flatMap((r) => r.children ?? []).find((c) => c.id.split(".")[1] === segments[0]);
  if (!collection) return null;
  const id = [collection.id, ...segments.slice(1)].join(".");
  return tree.byId.get(id) ?? null;
}

/** The path from the realm down to a node, inclusive. */
export function pathTo(tree: TreeIndex, id: string): CollectionNodeRecord[] {
  const out: CollectionNodeRecord[] = [];
  let current: string | undefined = id;
  while (current) {
    const node = tree.byId.get(current);
    if (!node) break;
    out.unshift(node);
    current = tree.parentOf.get(current);
  }
  return out;
}

export function localised(text: LocalisedText, lang: "en" | "es"): string {
  return text[lang] || text.en;
}
