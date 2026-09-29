// /map: where the specimens came from. Countries are shaded by how many slides hold a specimen from them; contributed
// slides with coordinates are points, obscured ones their 0.2 degree cell. The same filters as a search narrow it
// (in the address), and a selected country (?at=) shows its slides. The list of countries beside the map is its
// keyboard and screen-reader equivalent, and works when the map cannot (no WebGL).
import { lazy, Suspense, useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import { Link, useLocation, useSearchParams } from "wouter";
import { api } from "../../api/client";
import { useResource } from "../../api/useResource";
import { FacetPanel, valueLabel } from "../../explore/FacetPanel";
import { FACETS, activeCount, apiQuery, cleared, readFilters, toggle, writeFilters, type Facet } from "../../explore/filters";
import { useI18n } from "../../i18n";
import { shadeOpacity, SHADE_STEPS } from "../../map/style";
import { Place } from "../../router/Place";
import { trayReference } from "../../slide/names";
import { TraySlide } from "../../slide/TraySlide";
import { localised, useTree, type TreeIndex } from "../../tree/TreeProvider";
import { Button } from "../../ui/Button";
import { RemovableChip } from "../../ui/Chip";
import { Skeleton } from "../../ui/Feedback";
import { Glyph } from "../../ui/Icon";
import { Dialog } from "../../ui/Overlay";
import { TreeGate } from "../TreeGate";
import styles from "./MapPlace.module.css";

const MapCanvas = lazy(() => import("../../map/MapCanvas").then((m) => ({ default: m.MapCanvas })));
const PREVIEW = 6;

export function MapPlace() {
  const { t } = useI18n();
  const tree = useTree();
  const [ready, setReady] = useState(false);
  return (
    <Place title={t("map.title")} ready={ready} trail={[{ label: t("nav.collections"), href: "/" },
      { label: t("map.title") }]}>
      <p className={styles.intro}>{t("map.intro")}</p>
      <TreeGate tree={tree}>{(index) => <MapView tree={index} onReady={setReady} />}</TreeGate>
    </Place>
  );
}

function MapView({ tree, onReady }: { tree: TreeIndex; onReady: (ready: boolean) => void }) {
  const i18n = useI18n();
  const { t, plural, lang, number } = i18n;
  const [params, setParams] = useSearchParams();
  const [, navigate] = useLocation();
  const filters = useMemo(() => readFilters(params), [params]);
  const selected = params.get("at");
  const [dialog, setDialog] = useState(false);
  const [basemap, setBasemap] = useState<boolean | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  const write = (next: typeof filters, at: string | null = selected) => {
    const out = writeFilters(next);
    out.delete("n");
    if (at) out.set("at", at);
    setParams(out, { replace: true });
  };
  const select = useCallback((code: string | null) => {
    const out = new URLSearchParams(location.search);
    if (code) out.set("at", code); else out.delete("at");
    setParams(out, { replace: true });
  }, [setParams]);

  const query = apiQuery(filters);
  const data = useResource(`map?${query}`, (signal) => api.map(query, signal));
  const counts = useResource(`facets?${query}`, (signal) => api.facets(query, signal));
  const universeQuery = apiQuery(cleared(filters));
  const universe = useResource(`facets?${universeQuery}`, (signal) => api.facets(universeQuery, signal));
  const shapes = useResource("country-shapes", (signal) => api.countryShapes(signal));
  const previewQuery = selected ? apiQuery(filters, { limit: String(PREVIEW) }) : null;
  if (previewQuery && selected) previewQuery.set("country", selected);
  const preview = useResource(previewQuery ? `slides?${previewQuery}` : null,
    (signal) => api.slides(previewQuery!, signal));

  const map = data.value;
  const ready = data.state !== "loading" && shapes.state !== "loading";
  useEffect(() => onReady(ready), [ready, onReady]);

  const countries = Object.entries(map?.countries ?? {}).sort((a, b) => b[1] - a[1] ||
    (tree.countries[a[0]]?.[lang] ?? a[0]).localeCompare(tree.countries[b[0]]?.[lang] ?? b[0], lang));
  const placed = countries.reduce((n, [, c]) => n + c, 0);
  const name = (code: string) => tree.countries[code]?.[lang] ?? code;
  const chips = FACETS.flatMap((facet) => filters.values[facet].map((id) => ({ facet, id,
    label: valueLabel(facet, id, tree, i18n).label })));
  const scopeNode = filters.node ? tree.byId.get(filters.node) : undefined;
  const onToggle = (facet: Facet, value: string, on: boolean) => write(toggle(filters, facet, value, on));
  const active = activeCount(filters);
  const searchSelected = selected ? (() => {
    const q = writeFilters({ ...filters, values: { ...filters.values, country: [selected] } });
    q.delete("n");
    return `/search?${q}`;
  })() : "";

  return (
    <div className={styles.layout}>
      <div className={styles.mapColumn}>
        {unavailable ? (
          <p className={styles.notice} role="status"><Glyph name="info" size={20} />{t("map.unavailable")}</p>
        ) : shapes.value && map ? (
          <Suspense fallback={<div className={styles.placeholder}><Skeleton lines={3} /></div>}>
            <MapCanvas shapes={shapes.value} names={tree.countries} counts={map.countries} points={map.points}
              selected={selected} onSelectCountry={select} onOpenSlide={(id) => navigate(`/s/${id}`)}
              onBasemap={setBasemap} onUnavailable={() => setUnavailable(true)} />
          </Suspense>
        ) : (
          <div className={styles.placeholder}><Skeleton lines={3} /></div>
        )}
        <p className={styles.attribution}>
          {basemap === false ? `${t("map.nobasemap")} ` : ""}
          {basemap ? `${t("map.attribution.basemap")} ` : ""}{t("map.attribution")}
        </p>
      </div>

      <aside className={styles.panel} aria-label={t("map.panel")}>
        <div className={styles.summary}>
          <p className={styles.total} role="status">
            {map ? plural("count.slides", map.total) : t("state.loading")}
          </p>
          {map ? (
            <p className={styles.facts}>
              {t("map.placed", { slides: plural("count.slides", placed),
                countries: plural("count.countries", countries.length) })}
              {map.points.length ? ` ${t("map.points", { count: map.points.length })}` : ""}
            </p>
          ) : null}
          <Button icon="filter" onClick={() => setDialog(true)}>
            {active ? t("explore.filters.count", { count: active }) : t("explore.filters")}
          </Button>
        </div>

        {chips.length || scopeNode ? (
          <div className={styles.chips}>
            {scopeNode ? (
              <RemovableChip label={t("explore.scope", { name: localised(scopeNode.name, lang) })}
                onRemove={() => write({ ...filters, node: undefined })} />
            ) : null}
            {chips.map((c) => (
              <RemovableChip key={`${c.facet}-${c.id}`} label={c.label} onRemove={() => onToggle(c.facet, c.id, false)} />
            ))}
          </div>
        ) : null}

        <Legend />

        {selected ? (
          <section className={styles.selected} aria-labelledby="map-selected">
            <div className={styles.selectedHead}>
              <h2 id="map-selected" className={styles.selectedName}>{name(selected)}</h2>
              <Button variant="quiet" size="small" icon="close" onClick={() => select(null)}>{t("action.close")}</Button>
            </div>
            <p>{plural("count.slides", map?.countries[selected] ?? 0)}</p>
            {preview.value?.items.length ? (
              <ul className={styles.preview}
                style={{ "--ref": trayReference(preview.value.items.map((s) => s.format)) } as CSSProperties}>
                {preview.value.items.map((s) => <li key={s.id}><TraySlide slide={s} tree={tree} /></li>)}
              </ul>
            ) : preview.state === "loading" ? <Skeleton lines={2} /> : null}
            {(map?.countries[selected] ?? 0) > 0 ? (
              <Link href={searchSelected} className={styles.searchLink}>
                <Glyph name="search" size={20} />{t("map.country.search", { country: name(selected) })}
              </Link>
            ) : null}
          </section>
        ) : (
          <p className={styles.hint}>{t("map.select")}</p>
        )}

        <section aria-labelledby="map-countries">
          <h2 id="map-countries" className={styles.listTitle}>{t("map.countries")}</h2>
          {countries.length ? (
            <ul className={styles.countries}>
              {countries.map(([code, count]) => (
                <li key={code}>
                  <button type="button" className={styles.country} aria-pressed={selected === code}
                    style={{ "--shade": shadeOpacity(count) } as CSSProperties}
                    onClick={() => select(selected === code ? null : code)}>
                    <span className={styles.swatch} aria-hidden="true" />
                    <span>{name(code)}</span>
                    <span className={styles.countryCount}>{number(count)}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : map ? <p className={styles.hint}>{t("map.nocountries")}</p> : <Skeleton lines={4} />}
          {map && map.total > placed ? (
            <p className={styles.hint}>{t("map.unplaced", { slides: plural("count.slides", map.total - placed) })}</p>
          ) : null}
        </section>
      </aside>

      <Dialog open={dialog} title={t("explore.filters")} onClose={() => setDialog(false)}
        actions={<Button variant="primary" onClick={() => setDialog(false)}>
          {map ? t("explore.show.count", { count: map.total }) : t("explore.show")}
        </Button>}>
        <FacetPanel filters={filters} counts={counts.value} universe={universe.value} tree={tree} onToggle={onToggle} />
      </Dialog>
    </div>
  );
}

function Legend() {
  const { t } = useI18n();
  return (
    <figure className={styles.legend}>
      <figcaption>{t("map.legend")}</figcaption>
      <ul>
        {SHADE_STEPS.map((step, i) => (
          <li key={step} style={{ "--shade": shadeOpacity(step) } as CSSProperties}>
            <span className={styles.swatch} aria-hidden="true" />
            {i < SHADE_STEPS.length - 1 ? t("map.range", { from: step, to: SHADE_STEPS[i + 1] - 1 })
              : t("map.ormore", { count: step })}
          </li>
        ))}
        <li><span className={styles.point} aria-hidden="true" />{t("map.point")}</li>
        <li><span className={styles.cell} aria-hidden="true" />{t("map.cell")}</li>
      </ul>
    </figure>
  );
}
