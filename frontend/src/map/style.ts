// The map's style, built from the room's tokens (MapLibre cannot read CSS variables, so the colours are read from the
// page and applied again when the room changes). The basemap keeps only the ground and the water; the countries,
// their shading and their labels come from Laminario's own layers, labelled in the page's own face through
// MapLibre's `font-faces` (no glyph server).
import { layers, namedFlavor } from "@protomaps/basemaps";
import type { ExpressionSpecification, LayerSpecification, Map as MapLibre, StyleSpecification } from "maplibre-gl";

export interface MapColours {
  land: string;
  water: string;
  border: string;
  ink: string;
  inkMuted: string;
  accent: string;
  surface: string;
  focus: string;
}

export const LABEL_FONT = "Laminario Sans";
const BASEMAP_LAYERS = new Set(["background", "earth", "water", "water_river"]);

export function readColours(): MapColours {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string) => css.getPropertyValue(name).trim();
  return {
    land: v("--c-map-land"), water: v("--c-map-water"), border: v("--c-map-border"), ink: v("--c-ink"),
    inkMuted: v("--c-ink-muted"), accent: v("--c-accent"), surface: v("--c-surface"), focus: v("--c-focus"),
  };
}

/** The shading of a country by its slides: none at 0, then steps a legend can name. */
export const SHADE_STEPS = [1, 5, 20, 100] as const;
const SHADE: ExpressionSpecification = ["step", ["coalesce", ["feature-state", "count"], 0],
  0, 1, 0.2, 5, 0.34, 20, 0.5, 100, 0.66];

export function shadeOpacity(count: number): number {
  const stops = [[100, 0.66], [20, 0.5], [5, 0.34], [1, 0.2]] as const;
  return stops.find(([at]) => count >= at)?.[1] ?? 0;
}

export function buildStyle(c: MapColours, basemapUrl: string | null, origin: string): StyleSpecification {
  const base: LayerSpecification[] = basemapUrl
    ? layers("protomaps", { ...namedFlavor("light"), background: c.water, earth: c.land, water: c.water })
      .filter((l) => BASEMAP_LAYERS.has(l.id))
    : [{ id: "background", type: "background", paint: { "background-color": c.water } }];
  return {
    version: 8,
    "font-faces": { [LABEL_FONT]: [{ url: `${origin}/fonts/laminario-sans-roman.woff2` }] },
    sources: {
      ...(basemapUrl ? {
        protomaps: {
          type: "vector", url: `pmtiles://${basemapUrl}`, maxzoom: 7,
          attribution: "© OpenStreetMap contributors (ODbL), Protomaps",
        },
      } : {}),
      countries: { type: "geojson", data: { type: "FeatureCollection", features: [] }, promoteId: "code" },
      labels: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
      cells: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
      points: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
    },
    layers: [
      ...base,
      // Without the basemap the countries are the ground.
      ...(basemapUrl ? [] : [{ id: "countries-land", type: "fill", source: "countries",
        paint: { "fill-color": c.land } } as LayerSpecification]),
      { id: "countries-shade", type: "fill", source: "countries",
        paint: { "fill-color": c.accent, "fill-opacity": SHADE } },
      { id: "countries-line", type: "line", source: "countries",
        paint: {
          "line-color": ["case", ["boolean", ["feature-state", "selected"], false], c.accent, c.border],
          "line-width": ["case", ["boolean", ["feature-state", "selected"], false], 2.2,
            ["boolean", ["feature-state", "hover"], false], 1.4, 0.6],
        } },
      { id: "cells", type: "fill", source: "cells", paint: { "fill-color": c.focus, "fill-opacity": 0.16 } },
      { id: "cells-line", type: "line", source: "cells",
        paint: { "line-color": c.focus, "line-width": 1.2, "line-dasharray": [2, 2] } },
      { id: "points", type: "circle", source: "points",
        paint: { "circle-radius": 5, "circle-color": c.focus, "circle-stroke-color": c.surface,
          "circle-stroke-width": 1.5 } },
      { id: "labels-placed", type: "symbol", source: "labels", filter: [">", ["get", "count"], 0],
        layout: {
          "text-field": ["format", ["get", "name"], {}, "\n", {}, ["to-string", ["get", "count"]],
            { "font-scale": 0.85 }],
          "text-font": [LABEL_FONT], "text-size": 13, "symbol-sort-key": ["-", 0, ["get", "count"]],
          "text-max-width": 8,
        },
        paint: { "text-color": c.ink, "text-halo-color": c.land, "text-halo-width": 1.6 } },
      { id: "labels-other", type: "symbol", source: "labels", minzoom: 3,
        filter: ["all", ["==", ["get", "count"], 0], ["<=", ["get", "label_zoom"], ["literal", 4]]],
        layout: { "text-field": ["get", "name"], "text-font": [LABEL_FONT], "text-size": 11, "text-max-width": 7 },
        paint: { "text-color": c.inkMuted, "text-halo-color": c.land, "text-halo-width": 1.4 } },
      { id: "labels-late", type: "symbol", source: "labels", minzoom: 5,
        filter: ["all", ["==", ["get", "count"], 0], [">", ["get", "label_zoom"], ["literal", 4]]],
        layout: { "text-field": ["get", "name"], "text-font": [LABEL_FONT], "text-size": 11, "text-max-width": 7 },
        paint: { "text-color": c.inkMuted, "text-halo-color": c.land, "text-halo-width": 1.4 } },
    ],
  };
}

/** The room changed: every colour of the style again, without rebuilding the sources. */
export function repaint(map: MapLibre, c: MapColours, basemap: boolean): void {
  type Paint = Parameters<MapLibre["setPaintProperty"]>;
  const set = (layer: string, property: Paint[1], value: Paint[2]) => {
    if (map.getLayer(layer)) map.setPaintProperty(layer, property, value);
  };
  set("background", "background-color", c.water);
  if (basemap) {
    set("earth", "fill-color", c.land);
    set("water", "fill-color", c.water);
    set("water_river", "line-color", c.water);
  }
  set("countries-land", "fill-color", c.land);
  set("countries-shade", "fill-color", c.accent);
  set("countries-line", "line-color", ["case", ["boolean", ["feature-state", "selected"], false], c.accent, c.border]);
  set("cells", "fill-color", c.focus);
  set("cells-line", "line-color", c.focus);
  set("points", "circle-color", c.focus);
  set("points", "circle-stroke-color", c.surface);
  set("labels-placed", "text-color", c.ink);
  for (const layer of ["labels-placed", "labels-other", "labels-late"]) set(layer, "text-halo-color", c.land);
  set("labels-other", "text-color", c.inkMuted);
  set("labels-late", "text-color", c.inkMuted);
}
