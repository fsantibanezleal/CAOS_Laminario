// The MapLibre map of the map place. It owns the WebGL canvas and nothing else: the place gives it the countries'
// shapes, the counts, the points and the selection, and hears which country or slide was chosen. The basemap is read
// from the PMTiles file with byte ranges when it is installed (a HEAD request says so), and the map works without it.
import { addProtocol, Map as MapLibre, setWorkerUrl, type GeoJSONSource } from "maplibre-gl";
// MapLibre starts its worker from a file beside its own module, which a bundle does not have; Vite emits the worker
// as an ES module and gives its address.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import { Protocol } from "pmtiles";
import { useEffect, useRef, useState } from "react";
import { BASEMAP_URL, type CountryShapes } from "../api/client";
import type { MapPointRecord } from "../contract/catalog";
import { useRoom } from "../design/theme";
import { useI18n } from "../i18n";
import { IconButton } from "../ui/Button";
import { buildStyle, readColours, repaint } from "./style";
import styles from "./MapCanvas.module.css";

let protocolAdded = false;
type GeoJSONData = Parameters<GeoJSONSource["setData"]>[0];

export interface MapCanvasProps {
  shapes: CountryShapes;
  names: Record<string, { en: string; es: string }>;
  counts: Record<string, number>;
  points: MapPointRecord[];
  selected: string | null;
  onSelectCountry: (code: string | null) => void;
  onOpenSlide: (id: string) => void;
  onBasemap: (present: boolean) => void;
  /** WebGL is missing or the map failed to start; the place keeps its list. */
  onUnavailable: () => void;
}

export type Bounds = [number, number, number, number];
/** The inhabited world, from Tierra del Fuego to Svalbard: the first view. */
const WORLD: Bounds = [-170, -57, 180, 78];

/** The box around a country's shapes, for flying to it (the antimeridian is ignored: the box is the long way). */
export function boundsOf(shapes: CountryShapes, code: string): Bounds | null {
  const feature = shapes.features.find((f) => f.id === code);
  if (!feature) return null;
  let [w, s, e, n] = [180, 90, -180, -90];
  for (const poly of feature.geometry.coordinates) for (const [x, y] of poly[0]) {
    w = Math.min(w, x); e = Math.max(e, x); s = Math.min(s, y); n = Math.max(n, y);
  }
  return [w, s, e, n];
}

export function MapCanvas({ shapes, names, counts, points, selected, onSelectCountry, onOpenSlide, onBasemap,
  onUnavailable }: MapCanvasProps) {
  const { t, lang } = useI18n();
  const { room } = useRoom();
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibre | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [basemap, setBasemap] = useState<boolean | null>(null);
  const hovered = useRef<string | null>(null);
  const handlers = useRef({ onSelectCountry, onOpenSlide });
  handlers.current = { onSelectCountry, onOpenSlide };

  // Is the basemap installed? One HEAD request; a 404 means the countries are the ground.
  useEffect(() => {
    const controller = new AbortController();
    fetch(BASEMAP_URL, { method: "HEAD", signal: controller.signal }).then(
      (r) => setBasemap(r.ok), () => { if (!controller.signal.aborted) setBasemap(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => { if (basemap !== null) onBasemap(basemap); }, [basemap, onBasemap]);

  // The map itself, once the basemap question is answered.
  useEffect(() => {
    if (basemap === null || !container.current) return undefined;
    if (!protocolAdded) {
      setWorkerUrl(workerUrl);
      addProtocol("pmtiles", new Protocol().tile);
      protocolAdded = true;
    }
    let map: MapLibre;
    try {
      map = new MapLibre({
        container: container.current,
        style: buildStyle(readColours(), basemap ? `${location.origin}${BASEMAP_URL}` : null, location.origin),
        bounds: WORLD, fitBoundsOptions: { padding: 8 }, minZoom: 0.3, maxZoom: 9, renderWorldCopies: false,
        attributionControl: false, dragRotate: false, pitchWithRotate: false, touchPitch: false,
        cooperativeGestures: false,
        locale: { "Map.Title": t("map.canvas") },
      });
    } catch {
      onUnavailable();
      return undefined;
    }
    map.touchZoomRotate.disableRotation();
    map.keyboard.disableRotation();
    mapRef.current = map;
    map.on("load", () => setLoaded(true));
    map.on("error", (e) => {
      // A missing tile or a font is drawn around; only a failure to start takes the map away.
      if (!map.loaded() && /webgl/i.test(String(e.error?.message))) onUnavailable();
    });
    map.on("click", "points", (e) => {
      const id = e.features?.[0]?.properties?.id;
      if (id) handlers.current.onOpenSlide(String(id));
    });
    map.on("click", (e) => {
      if (map.queryRenderedFeatures(e.point, { layers: ["points"] }).length) return;
      const hit = map.queryRenderedFeatures(e.point, { layers: ["countries-shade"] })[0];
      handlers.current.onSelectCountry(hit?.id ? String(hit.id) : null);
    });
    map.on("mousemove", "countries-shade", (e) => {
      const id = e.features?.[0]?.id ? String(e.features[0].id) : null;
      if (hovered.current && hovered.current !== id) {
        map.setFeatureState({ source: "countries", id: hovered.current }, { hover: false });
      }
      hovered.current = id;
      if (id) map.setFeatureState({ source: "countries", id }, { hover: true });
      map.getCanvas().style.cursor = id ? "pointer" : "";
    });
    map.on("mouseleave", "countries-shade", () => {
      if (hovered.current) map.setFeatureState({ source: "countries", id: hovered.current }, { hover: false });
      hovered.current = null;
      map.getCanvas().style.cursor = "";
    });
    map.on("mouseenter", "points", () => { map.getCanvas().style.cursor = "pointer"; });
    return () => {
      map.remove();
      mapRef.current = null;
      setLoaded(false);
    };
    // The map is made once per basemap answer; the language, room and data are applied by the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [basemap]);

  // The shapes, once.
  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    (map.getSource("countries") as GeoJSONSource).setData(shapes as unknown as GeoJSONData);
  }, [loaded, shapes]);

  // The counts as feature state (the shading) and the labels with their names in the page's language.
  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    for (const f of shapes.features) map.setFeatureState({ source: "countries", id: f.id }, { count: counts[f.id] ?? 0 });
    (map.getSource("labels") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: shapes.features.map((f) => ({
        type: "Feature", geometry: { type: "Point", coordinates: f.properties.label },
        properties: { code: f.id, name: names[f.id]?.[lang] ?? f.id, count: counts[f.id] ?? 0,
          label_zoom: f.properties.label_zoom },
      })),
    });
  }, [loaded, shapes, counts, names, lang]);

  // Points, and obscured slides' cells.
  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    (map.getSource("points") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: points.map((p) => ({ type: "Feature", geometry: { type: "Point", coordinates: [p.lon, p.lat] },
        properties: { id: p.id, obscured: p.obscured } })),
    });
    (map.getSource("cells") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: points.filter((p) => p.cell).map((p) => {
        const c = p.cell!;
        return { type: "Feature", properties: { id: p.id }, geometry: { type: "Polygon",
          coordinates: [[[c.west, c.south], [c.east, c.south], [c.east, c.north], [c.west, c.north], [c.west, c.south]]] } };
      }),
    });
  }, [loaded, points]);

  // The selection: marked, and flown to.
  const previous = useRef<string | null>(null);
  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    if (previous.current) map.setFeatureState({ source: "countries", id: previous.current }, { selected: false });
    previous.current = selected;
    if (!selected) return;
    map.setFeatureState({ source: "countries", id: selected }, { selected: true });
    const box = boundsOf(shapes, selected);
    if (box && box[2] - box[0] < 180) {
      map.fitBounds([[box[0], box[1]], [box[2], box[3]]], { padding: 40, maxZoom: 6,
        duration: matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 600 });
    }
  }, [loaded, selected, shapes]);

  // The room: every colour again.
  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    repaint(map, readColours(), Boolean(basemap));
  }, [loaded, room, basemap]);

  const zoom = (by: number) => mapRef.current?.zoomTo(mapRef.current.getZoom() + by,
    { duration: matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 250 });

  return (
    <div className={styles.frame}>
      <div ref={container} className={styles.canvas} />
      <div className={styles.controls}>
        <IconButton icon="plus" label={t("map.zoomin")} variant="secondary" onClick={() => zoom(1)} />
        <IconButton icon="minus" label={t("map.zoomout")} variant="secondary" onClick={() => zoom(-1)} />
        <IconButton icon="language" label={t("map.world")} variant="secondary" onClick={() => {
          handlers.current.onSelectCountry(null);
          mapRef.current?.fitBounds(WORLD, { padding: 8,
            duration: matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 600 });
        }} />
      </div>
    </div>
  );
}
