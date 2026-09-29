// The slides of a place with its filters: a drawer (scoped to its node) or a search (over the whole collection, or
// one cabinet). The filters live in the address and change it in place (replace, not a new history entry per chip),
// the results count is announced politely, and pages of 48 grow on request, never by themselves.
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "wouter";
import { api } from "../api/client";
import { useResource } from "../api/useResource";
import { useI18n } from "../i18n";
import type { MessageKey } from "../i18n/en";
import { trayReference } from "../slide/names";
import { TraySlide } from "../slide/TraySlide";
import { localised, type TreeIndex } from "../tree/TreeProvider";
import { Button } from "../ui/Button";
import { RemovableChip } from "../ui/Chip";
import { EmptyState, Skeleton } from "../ui/Feedback";
import { SearchField, Select } from "../ui/Field";
import { Dialog } from "../ui/Overlay";
import { FacetPanel, valueLabel } from "./FacetPanel";
import {
  FACETS, PAGE, activeCount, apiQuery, cleared, readFilters, sortOf, toggle, writeFilters, type Facet, type Filters,
  type Sort,
} from "./filters";
import styles from "./Explorer.module.css";
import { useSlidePages } from "./useSlidePages";

export interface ExplorerProps {
  tree: TreeIndex;
  /** The node the place is scoped to (a drawer); a search reads ``node`` from the address instead. */
  node?: string;
  /** Offer the collections a search reaches, as a facet that sets the node. */
  collections?: boolean;
  /** The drawer's own search field, and its label (a search place names it for the whole collection). */
  searchField?: boolean;
  searchLabel?: string;
  /** Facets the place offers; all by default. */
  only?: readonly Facet[];
  emptyTitle: string;
  emptyBody: string;
  onReady?: (ready: boolean) => void;
}

/** Typing waits this long after the last keystroke before it searches. */
const QUIET_MS = 250;

export function useFilters(): [Filters, (next: Filters) => void] {
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => readFilters(params), [params]);
  return [filters, (next) => setParams(writeFilters(next), { replace: true })];
}

export function Explorer({ tree, node, collections = false, searchField = true, searchLabel, only, emptyTitle,
  emptyBody, onReady }: ExplorerProps) {
  const i18n = useI18n();
  const { t, plural, lang } = i18n;
  const [filters, setFilters] = useFilters();
  const [draft, setDraft] = useState(filters.q);
  const [dialog, setDialog] = useState(false);
  const scope = node ?? filters.node;
  const sort = sortOf(filters);

  // The field follows the address (back, forward, a chip removed) and writes to it when the visitor pauses.
  useEffect(() => setDraft(filters.q), [filters.q]);
  const timer = useRef<number>(undefined);
  const type = (value: string) => {
    setDraft(value);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setFilters({ ...filters, q: value, shown: PAGE }), QUIET_MS);
  };
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const query = apiQuery(filters, { sort }, scope);
  const pages = useSlidePages(query, filters.shown);
  const facetQuery = apiQuery(filters, {}, scope);
  const counts = useResource(`facets?${facetQuery}`, (signal) => api.facets(facetQuery, signal));
  const universeQuery = apiQuery(cleared(filters), {}, scope);
  const universe = useResource(`facets?${universeQuery}`, (signal) => api.facets(universeQuery, signal));

  const ready = !pages.loading;
  useEffect(() => onReady?.(ready), [ready, onReady]);

  const change = (next: Filters) => setFilters(next);
  const onToggle = (facet: Facet, value: string, on: boolean) => change(toggle(filters, facet, value, on));
  const active = activeCount(filters);
  const total = pages.total;

  const chips = FACETS.flatMap((facet) => filters.values[facet].map((id) => ({ facet, id,
    label: valueLabel(facet, id, tree, i18n).label })));
  const scopeNode = !node && filters.node ? tree.byId.get(filters.node) : undefined;

  const panel = (
    <>
      {collections ? (
        <CollectionFacet tree={tree} current={filters.node} counts={counts.value?.collection}
          onChange={(id) => change({ ...filters, node: id, shown: PAGE })} />
      ) : null}
      <FacetPanel filters={filters} counts={counts.value} universe={universe.value} tree={tree} only={only}
        onToggle={onToggle} />
    </>
  );

  const sorts: Sort[] = filters.q.trim() ? ["relevance", "newest", "name"] : ["newest", "name"];

  return (
    <div className={styles.explorer}>
      <aside className={styles.rail} aria-label={t("explore.filters")}>{panel}</aside>

      <section className={styles.results} aria-busy={pages.loading || undefined}>
        <div className={styles.toolbar}>
          {searchField ? (
            <div className={styles.search}>
              <SearchField label={searchLabel ?? t("explore.within")} value={draft} onChange={(e) => type(e.target.value)}
                onClear={() => type("")} />
            </div>
          ) : null}
          <div className={styles.controls}>
            <p className={styles.count} role="status">
              {total === null ? t("state.loading") : plural("count.slides", total)}
            </p>
            <Button className={styles.filtersButton} icon="filter" onClick={() => setDialog(true)}>
              {active ? t("explore.filters.count", { count: active }) : t("explore.filters")}
            </Button>
            <div className={styles.sort}>
              <Select label={t("explore.sort")} value={sort}
                options={sorts.map((s) => ({ value: s, label: t(`explore.sort.${s}` as MessageKey) }))}
                onChange={(e) => change({ ...filters, sort: e.target.value as Sort, shown: PAGE })} />
            </div>
          </div>
        </div>

        {chips.length || scopeNode ? (
          <div className={styles.active}>
            {scopeNode ? (
              <RemovableChip label={t("explore.scope", { name: localised(scopeNode.name, lang) })}
                onRemove={() => change({ ...filters, node: undefined, shown: PAGE })} />
            ) : null}
            {chips.map((c) => (
              <RemovableChip key={`${c.facet}-${c.id}`} label={c.label} onRemove={() => onToggle(c.facet, c.id, false)} />
            ))}
            {chips.length > 1 ? (
              <Button variant="quiet" size="small" onClick={() => change(cleared(filters))}>
                {t("explore.filters.clear")}
              </Button>
            ) : null}
          </div>
        ) : null}

        {pages.error ? (
          <div className={styles.error} role="alert">
            <p>{t("explore.error")}</p>
            <Button onClick={pages.retry}>{t("explore.retry")}</Button>
          </div>
        ) : null}

        {total === null && !pages.error ? <Skeleton lines={4} /> : null}

        {total === 0 ? (
          <EmptyState icon={scope ?? "life"} title={emptyTitle}
            action={active || filters.q ? (
              <Button onClick={() => change({ ...cleared(filters), q: "" })}>{t("explore.filters.clear")}</Button>
            ) : undefined}>
            {emptyBody}
          </EmptyState>
        ) : null}

        {pages.items.length ? (
          <ul className={[styles.tray, pages.loading ? styles.stale : ""].join(" ")}
            style={{ "--ref": trayReference(pages.items.map((s) => s.format)) } as React.CSSProperties}>
            {pages.items.map((slide) => (
              <li key={slide.id}><TraySlide slide={slide} tree={tree} /></li>
            ))}
          </ul>
        ) : null}

        {total !== null && total > 0 ? (
          <div className={styles.more}>
            <p>{t("explore.showing", { shown: Math.min(pages.items.length, total), total })}</p>
            {pages.items.length < total ? (
              <Button busy={pages.loading} onClick={() => change({ ...filters, shown: filters.shown + PAGE })}>
                {t("explore.more", { count: Math.min(PAGE, total - pages.items.length) })}
              </Button>
            ) : null}
          </div>
        ) : null}
      </section>

      <Dialog open={dialog} title={t("explore.filters")} onClose={() => setDialog(false)}
        actions={<Button variant="primary" onClick={() => setDialog(false)}>
          {total === null ? t("explore.show") : t("explore.show.count", { count: total })}
        </Button>}>
        {panel}
      </Dialog>
    </div>
  );
}

function CollectionFacet({ tree, current, counts, onChange }: {
  tree: TreeIndex; current?: string; counts?: Record<string, number>; onChange: (id: string | undefined) => void;
}) {
  const { t, lang, number } = useI18n();
  const shown = tree.realms.flatMap((r) => r.children ?? []).filter((c) => (counts?.[c.id] ?? 0) > 0 || c.id === current);
  if (!shown.length) return null;
  return (
    <fieldset className={styles.collections}>
      <legend className={styles.legend}>{t("facet.collection")}</legend>
      <ul>
        {shown.map((c) => {
          const pressed = current === c.id || Boolean(current?.startsWith(`${c.id}.`));
          return (
            <li key={c.id}>
              <button type="button" aria-pressed={pressed} className={styles.collection}
                style={{ "--tag-hue": `var(--h-${c.id.split(".")[1]})` } as React.CSSProperties}
                onClick={() => onChange(pressed ? undefined : c.id)}>
                <svg width={20} height={20} viewBox="0 0 32 32" aria-hidden="true"><use href={`/icons.svg#${c.id}`} /></svg>
                <span>{localised(c.name, lang)}</span>
                <span className={styles.collectionCount}>{number(counts?.[c.id] ?? 0)}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </fieldset>
  );
}
