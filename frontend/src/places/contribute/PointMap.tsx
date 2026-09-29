// The specimen's point, set by a click on the map (the fields beside it are the other way): the point, the circle of
// its uncertainty, and the positions the photographs carry, which a click can adopt. The map is the explore map's
// style (the same basemap, the same rooms); it is only drawn for the contributor, whatever the case's geoprivacy.
import { addProtocol, Map as MapLibre, setWorkerUrl, type GeoJSONSource } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import { Protocol } from "pmtiles";
import { useEffect, useRef, useState } from "react";
import { api, BASEMAP_URL } from "../../api/client";
import { useRoom } from "../../design/theme";
import { useI18n } from "../../i18n";
import { buildStyle, readColours, repaint } from "../../map/style";
import styles from "./Contribute.module.css";

let protocolAdded = false;
type Data = Parameters<GeoJSONSource["setData"]>[0];

export interface LatLon {
  lat: number;
  lon: number;
}

/** A circle of ``metres`` around a point, as a polygon of 64 vertices (on a sphere of the mean Earth radius). */
export function circle(center: LatLon, metres: number): number[][] {
  const R = 6_371_008.8;
  const d = metres / R;
  const lat1 = (center.lat * Math.PI) / 180;
  const lon1 = (center.lon * Math.PI) / 180;
  const ring: number[][] = [];
  for (let i = 0; i <= 64; i += 1) {
    const b = (2 * Math.PI * i) / 64;
    const lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(b));
    const lon2 = lon1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(lat1), Math.cos(d) - Math.sin(lat1) * Math.sin(lat2));
    ring.push([(lon2 * 180) / Math.PI, (lat2 * 180) / Math.PI]);
  }
  return ring;
}

export function PointMap({ point, uncertainty, photos, onPick }: { point: LatLon | null; uncertainty: number | null;
  photos: LatLon[]; onPick: (p: LatLon) => void }) {
  const { t } = useI18n();
  const { room } = useRoom();
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibre | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const [basemap, setBasemap] = useState<boolean | null>(null);
  // Set once the countries are drawn: the map says what it drew (a gate waits for it, not for a timer).
  const [drawn, setDrawn] = useState(false);
  const pick = useRef(onPick);
  pick.current = onPick;

  useEffect(() => {
    const controller = new AbortController();
    fetch(BASEMAP_URL, { method: "HEAD", signal: controller.signal }).then((r) => setBasemap(r.ok),
      () => { if (!controller.signal.aborted) setBasemap(false); });
    return () => controller.abort();
  }, []);

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
        center: point ? [point.lon, point.lat] : [-40, 0], zoom: point ? 6 : 0.6, maxZoom: 12,
        renderWorldCopies: false, attributionControl: false, dragRotate: false, pitchWithRotate: false,
        locale: { "Map.Title": t("place.map") },
      });
    } catch {
      setUnavailable(true);
      return undefined;
    }
    map.touchZoomRotate.disableRotation();
    mapRef.current = map;
    map.getCanvas().style.cursor = "crosshair";
    map.on("load", () => {
      api.countryShapes().then((shapes) => {
        (map.getSource("countries") as GeoJSONSource | undefined)?.setData(shapes as unknown as Data);
        map.once("idle", () => setDrawn(true));
      }, () => undefined);
      map.addSource("photos", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({ id: "photos", type: "circle", source: "photos", paint: { "circle-radius": 6,
        "circle-color": "rgba(0,0,0,0)", "circle-stroke-width": 2, "circle-stroke-color": readColours().accent } });
      setLoaded(true);
    });
    map.on("click", (e) => {
      const hit = map.queryRenderedFeatures(e.point, { layers: ["photos"] })[0];
      const coordinates = hit?.geometry.type === "Point" ? hit.geometry.coordinates : [e.lngLat.lng, e.lngLat.lat];
      pick.current({ lat: Number(coordinates[1].toFixed(6)), lon: Number(coordinates[0].toFixed(6)) });
    });
    map.on("error", (e) => {
      if (!map.loaded() && /webgl/i.test(String(e.error?.message))) setUnavailable(true);
    });
    return () => {
      map.remove();
      mapRef.current = null;
      setLoaded(false);
    };
    // Made once per basemap answer; the point and the room are applied below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [basemap]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    (map.getSource("points") as GeoJSONSource).setData({ type: "FeatureCollection", features: point
      ? [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [point.lon, point.lat] } }] : [] });
    (map.getSource("cells") as GeoJSONSource).setData({ type: "FeatureCollection", features: point && uncertainty
      ? [{ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [circle(point, uncertainty)] } }]
      : [] });
    (map.getSource("photos") as GeoJSONSource).setData({ type: "FeatureCollection", features: photos.map((p) => ({
      type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [p.lon, p.lat] } })) });
  }, [loaded, point, uncertainty, photos]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map || !point) return;
    const bounds = map.getBounds();
    if (!bounds.contains([point.lon, point.lat])) map.jumpTo({ center: [point.lon, point.lat], zoom: Math.max(map.getZoom(), 5) });
  }, [loaded, point]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    repaint(map, readColours(), Boolean(basemap));
  }, [loaded, room, basemap]);

  if (unavailable) return <p className={styles.fieldHint}>{t("place.mapUnavailable")}</p>;
  return (
    <div className={styles.pointMap} data-drawn={drawn || undefined}>
      <div ref={container} className={styles.pointMapCanvas} aria-label={t("place.map")} role="region" />
      <p className={styles.fieldHint}>{t("place.map.hint")}</p>
    </div>
  );
}
