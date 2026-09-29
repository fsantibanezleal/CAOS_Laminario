// The microscope stage: OpenSeadragon over the asset's IIIF image, with the objectives the pixel size allows
// (R-1104), a scale bar recomputed on every change of the view (R-086), a stack's planes kept aligned and named by
// depth (R-1105), a polarised pair's two images cross-faded and the view rotated (R-1106), and the annotations of the
// image drawn by Annotorious (R-1108). Loaded only on the stage place.
import { createOSDAnnotator, W3CImageFormat, type ImageAnnotation } from "@annotorious/openseadragon";
import "@annotorious/openseadragon/annotorious-openseadragon.css";
import OpenSeadragon from "openseadragon";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { AnnotationRecord, AssetRecord } from "../contract/catalog";
import { useI18n } from "../i18n";
import type { MessageKey } from "../i18n/en";
import type { StageItem } from "../slide/assets";
import { Button } from "../ui/Button";
import { TextField } from "../ui/Field";
import { Glyph } from "../ui/Icon";
import { Dialog } from "../ui/Overlay";
import { objectiveAt, scaleBar, turret, type ScaleBar } from "./optics";
import styles from "./StageViewer.module.css";

type Annotator = ReturnType<typeof createOSDAnnotator<ImageAnnotation, ImageAnnotation>>;

function tileSource(asset: AssetRecord): string | OpenSeadragon.TileSourceOptions {
  if (asset.media.iiif_info_url) return asset.media.iiif_info_url;
  return { type: "image", url: asset.media.image_url ?? "" } as OpenSeadragon.TileSourceOptions;
}

/** The IIIF image id (or plain image address) the annotations of an asset point at. */
export function annotationSource(asset: AssetRecord): string {
  return asset.media.iiif_info_url?.replace(/\/info\.json$/, "") ?? asset.media.image_url ?? "";
}

const reducedMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

export interface StageViewerProps {
  slideId: string;
  item: StageItem;
  signedIn: boolean;
}

export function StageViewer({ slideId, item, signedIn }: StageViewerProps) {
  const { t, number, plural } = useI18n();
  const host = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<OpenSeadragon.Viewer | null>(null);
  const annoRef = useRef<Annotator | null>(null);
  const [plane, setPlane] = useState(0);
  const [composite, setComposite] = useState<AssetRecord | null>(null);
  const [polar, setPolar] = useState<"ppl" | "xpl">("ppl");
  const [rotation, setRotation] = useState(0);
  const [bar, setBar] = useState<ScaleBar | null>(null);
  const [objective, setObjective] = useState<number | null>(null);
  const [notes, setNotes] = useState<AnnotationRecord[]>([]);
  const [shown, setShown] = useState(true);
  const [tool, setTool] = useState<"rectangle" | "polygon" | null>(null);
  const [drafting, setDrafting] = useState<ImageAnnotation | null>(null);
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState<"loading" | "ready" | "failed">("loading");

  const visible: AssetRecord = composite ?? (item.kind === "stack" ? item.planes[plane] : item.kind === "pair"
    ? (polar === "ppl" ? item.ppl! : item.xpl!) : item.first);
  const pixelUm = visible.pixel_size_um ?? item.pixelUm;
  const steps = useMemo(() => turret(pixelUm), [pixelUm]);

  // The readout and the scale bar, from the view as it is drawn.
  const measure = useCallback(() => {
    const viewer = viewerRef.current;
    if (!viewer || !viewer.world.getItemCount()) return;
    const imageZoom = viewer.world.getItemAt(0).viewportToImageZoom(viewer.viewport.getZoom(true));
    if (pixelUm && imageZoom > 0) {
      setBar(scaleBar(pixelUm / imageZoom, viewer.container.clientWidth));
      setObjective(objectiveAt(pixelUm, imageZoom));
    } else {
      setBar(null);
      setObjective(null);
    }
  }, [pixelUm]);

  // The viewer, once per item.
  useEffect(() => {
    if (!host.current) return undefined;
    const viewer = OpenSeadragon({
      element: host.current, prefixUrl: "", showNavigationControl: false, showNavigator: true,
      navigatorPosition: "TOP_RIGHT", navigatorSizeRatio: 0.16, crossOriginPolicy: "Anonymous",
      gestureSettingsMouse: { clickToZoom: false, dblClickToZoom: true },
      maxZoomPixelRatio: 6, visibilityRatio: 0.3, minZoomImageRatio: 0.5,
      animationTime: reducedMotion() ? 0 : 0.6, springStiffness: 8,
    });
    viewerRef.current = viewer;
    const sources = item.kind === "pair" ? [item.ppl!, item.xpl!] : [item.kind === "stack" ? item.planes[0] : item.first];
    viewer.open(sources.map((a, i) => ({ tileSource: tileSource(a), opacity: i === 0 ? 1 : 0 })) as never);
    viewer.addHandler("open", () => { setStatus("ready"); measure(); });
    viewer.addHandler("open-failed", () => setStatus("failed"));
    viewer.addHandler("viewport-change", measure);
    viewer.addHandler("resize", measure);
    const anno = createOSDAnnotator<ImageAnnotation, ImageAnnotation>(viewer, {
      adapter: W3CImageFormat(annotationSource(sources[0])) as never, drawingEnabled: false,
      style: { stroke: "#58ccff", strokeWidth: 2, fill: "#58ccff", fillOpacity: 0.12 },
    });
    anno.on("createAnnotation", (created) => setDrafting(created));
    annoRef.current = anno;
    return () => {
      anno.destroy();
      viewer.destroy();
      viewerRef.current = null;
      annoRef.current = null;
    };
    // One viewer per stage item; plane, polar and rotation are applied below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.key]);

  // A stack's plane (or a composite): the new image goes on top and the old one leaves once the new one is drawn, so
  // the view never goes blank and never moves (all planes have the same size and place).
  const shownAsset = useRef<number>(visible.id);
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || item.kind !== "stack" || status !== "ready" || shownAsset.current === visible.id) return;
    shownAsset.current = visible.id;
    const old = viewer.world.getItemAt(viewer.world.getItemCount() - 1);
    viewer.addTiledImage({
      tileSource: tileSource(visible) as never, index: viewer.world.getItemCount(), opacity: 1,
      success: (event: { item: OpenSeadragon.TiledImage }) => {
        const swap = () => { if (old && viewer.world.getIndexOfItem(old) >= 0) viewer.world.removeItem(old); };
        if (event.item.getFullyLoaded()) swap();
        else event.item.addOnceHandler("fully-loaded-change", swap);
        window.setTimeout(swap, 4000);
      },
    } as never);
  }, [visible, item.kind, status]);

  // A polarised pair: cross-fade to the chosen image (at once under reduced motion).
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || item.kind !== "pair" || viewer.world.getItemCount() < 2) return undefined;
    const xpl = viewer.world.getItemAt(1);
    const target = polar === "xpl" ? 1 : 0;
    if (reducedMotion()) {
      xpl.setOpacity(target);
      return undefined;
    }
    const start = xpl.getOpacity();
    const began = performance.now();
    let frame = 0;
    const step = (now: number) => {
      const k = Math.min(1, (now - began) / 240);
      xpl.setOpacity(start + (target - start) * k);
      if (k < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [polar, item.kind, status]);

  useEffect(() => {
    viewerRef.current?.viewport.setRotation(rotation, reducedMotion());
  }, [rotation]);

  // The annotations of the image on view.
  useEffect(() => {
    const controller = new AbortController();
    api.annotations(slideId, visible.id, controller.signal).then((list) => {
      setNotes(list);
      annoRef.current?.setAnnotations(list.map((r) => r.annotation) as never);
    }, () => undefined);
    return () => controller.abort();
  }, [slideId, visible.id, status]);

  useEffect(() => {
    annoRef.current?.setVisible?.(shown);
  }, [shown]);

  useEffect(() => {
    const anno = annoRef.current;
    if (!anno) return;
    anno.setDrawingEnabled(tool !== null);
    if (tool) anno.setDrawingTool(tool);
  }, [tool]);

  const zoomTo = (screenPerImage: number) => {
    const viewer = viewerRef.current;
    if (!viewer || !viewer.world.getItemCount()) return;
    viewer.viewport.zoomTo(viewer.world.getItemAt(0).imageToViewportZoom(screenPerImage), undefined, reducedMotion());
  };

  const saveDraft = async () => {
    const anno = annoRef.current;
    if (!drafting || !anno) return;
    const w3c = anno.getAnnotationById(drafting.id) as unknown as { target: unknown };
    try {
      const saved = await api.addAnnotation(slideId, visible.id, {
        body: [{ type: "TextualBody", value: comment.trim(), purpose: "commenting" }], target: w3c.target });
      anno.removeAnnotation(drafting.id);
      if (saved) {
        anno.addAnnotation(saved.annotation as never);
        setNotes((list) => [...list, saved]);
      }
    } catch {
      anno.removeAnnotation(drafting.id);
    }
    setDrafting(null);
    setComment("");
    setTool(null);
  };

  const cancelDraft = () => {
    if (drafting) annoRef.current?.removeAnnotation(drafting.id);
    setDrafting(null);
    setComment("");
  };

  const remove = async (record: AnnotationRecord) => {
    await api.removeAnnotation(record.id);
    annoRef.current?.removeAnnotation(String(record.annotation.id));
    setNotes((list) => list.filter((n) => n.id !== record.id));
  };

  return (
    <div className={styles.stage}>
      <div className={styles.viewport}>
        <div ref={host} className={styles.viewer} data-testid="stage-viewer" data-asset={visible.id}
          data-rotation={rotation} role="application" aria-label={t("stage.viewer")} tabIndex={0} />
        {status === "failed" ? <p className={styles.failed} role="alert">{t("stage.failed")}</p> : null}
        {bar ? (
          <div className={styles.scale} data-testid="scale-bar" data-um={bar.um} data-px={bar.px}>
            <span className={styles.bar} style={{ width: `${bar.px}px` }} />
            <span>{number(bar.value)} {bar.unit}</span>
          </div>
        ) : (
          <p className={styles.unscaled}>{t("stage.unscaled")}</p>
        )}
        {objective ? (
          <p className={styles.readout} data-testid="readout">
            {t("stage.readout", { objective: number(objective, { maximumFractionDigits: objective < 10 ? 1 : 0 }) })}
          </p>
        ) : null}
      </div>

      <div className={styles.controls}>
        {steps.length ? (
          <fieldset className={styles.turret}>
            <legend>{t("stage.objectives")}</legend>
            {steps.map((s) => (
              <button key={s.objective} type="button" data-objective={s.objective} data-digital={s.digital}
                aria-pressed={objective !== null && Math.abs(objective - s.objective) / s.objective < 0.02}
                className={s.digital ? styles.digital : undefined} onClick={() => zoomTo(s.zoom)}
                title={s.digital ? t("stage.digital") : t("stage.optical", { um: number(s.umPerScreenPixel) })}>
                {s.objective}x{s.digital ? <span className={styles.digitalMark}>{t("stage.digital.short")}</span> : null}
              </button>
            ))}
          </fieldset>
        ) : null}
        <div className={styles.row}>
          <Button size="small" onClick={() => viewerRef.current?.viewport.goHome(reducedMotion())}>{t("stage.whole")}</Button>
          <Button size="small" onClick={() => setRotation((r) => (r + 270) % 360)}>{t("stage.rotate.left")}</Button>
          <Button size="small" onClick={() => setRotation((r) => (r + 90) % 360)}>{t("stage.rotate.right")}</Button>
          <span className={styles.angle} data-testid="rotation">{t("stage.rotation", { deg: rotation })}</span>
        </div>

        {item.kind === "stack" ? (
          <div className={styles.planes}>
            <label htmlFor="stage-plane">
              {t("stage.plane", { depth: number(item.planes[plane].plane?.depth_um ?? 0) })}
              <span className={styles.muted}> · {t("stage.plane.of", { n: plane + 1, count: item.planes.length })}</span>
            </label>
            <input id="stage-plane" type="range" min={0} max={item.planes.length - 1} step={1} value={plane}
              disabled={composite !== null} data-testid="plane"
              aria-valuetext={`${number(item.planes[plane].plane?.depth_um ?? 0)} µm`}
              onChange={(e) => setPlane(Number(e.target.value))} />
            {item.composites.length ? (
              <div className={styles.row} role="group" aria-label={t("stage.composites")}>
                <Button size="small" aria-pressed={composite === null} onClick={() => setComposite(null)}>
                  {t("stage.planes")}
                </Button>
                {item.composites.map((c) => (
                  <Button key={c.id} size="small" aria-pressed={composite?.id === c.id} onClick={() => setComposite(c)}>
                    {t(`role.${c.role}` as MessageKey)}
                  </Button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {item.kind === "pair" ? (
          <div className={styles.row} role="group" aria-label={t("stage.polars")}>
            <Button size="small" aria-pressed={polar === "ppl"} data-polar="ppl" onClick={() => setPolar("ppl")}>
              {t("stage.ppl")}
            </Button>
            <Button size="small" aria-pressed={polar === "xpl"} data-polar="xpl" onClick={() => setPolar("xpl")}>
              {t("stage.xpl")}
            </Button>
          </div>
        ) : null}

        <section className={styles.notes} aria-labelledby="stage-notes">
          <div className={styles.notesHead}>
            <h2 id="stage-notes">{plural("count.annotations", notes.length)}</h2>
            <Button size="small" variant="quiet" onClick={() => setShown((s) => !s)}>
              {shown ? t("stage.notes.hide") : t("stage.notes.show")}
            </Button>
          </div>
          {signedIn ? (
            <div className={styles.row} role="group" aria-label={t("stage.draw")}>
              <Button size="small" aria-pressed={tool === "rectangle"} onClick={() => setTool(tool === "rectangle" ? null : "rectangle")}>
                {t("stage.draw.rectangle")}
              </Button>
              <Button size="small" aria-pressed={tool === "polygon"} onClick={() => setTool(tool === "polygon" ? null : "polygon")}>
                {t("stage.draw.polygon")}
              </Button>
            </div>
          ) : <p className={styles.muted}>{t("stage.notes.signin")}</p>}
          <ul>
            {notes.map((n) => {
              const body = (n.annotation.body as { value?: string }[] | undefined)?.[0]?.value ?? "";
              return (
                <li key={n.id}>
                  <button type="button" className={styles.noteText}
                    onClick={() => annoRef.current?.fitBounds(String(n.annotation.id), { immediately: reducedMotion() })}>
                    {body || t("stage.notes.untitled")}
                  </button>
                  <span className={styles.muted}>{n.author}</span>
                  {n.removable ? (
                    <Button size="small" variant="quiet" onClick={() => remove(n)}>{t("action.remove", { name: "" }).trim()}</Button>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </section>
      </div>

      <Dialog open={drafting !== null} title={t("stage.notes.new")} onClose={cancelDraft}
        actions={<>
          <Button variant="quiet" onClick={cancelDraft}>{t("action.cancel")}</Button>
          <Button variant="primary" disabled={!comment.trim()} onClick={saveDraft}>{t("stage.notes.save")}</Button>
        </>}>
        <TextField label={t("stage.notes.text")} value={comment} maxLength={2000} onChange={(e) => setComment(e.target.value)} />
        <p className={styles.muted}><Glyph name="info" size={16} /> {t("stage.notes.public")}</p>
      </Dialog>
    </div>
  );
}
