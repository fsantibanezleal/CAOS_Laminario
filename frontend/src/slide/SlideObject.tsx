// The slide as an object: the server's drawing in millimetres (R-1101), inlined so it takes the room's colours and the
// page's label face. The glass follows the pointer a few degrees, as a slide tilted in the hand catches the light;
// with reduced motion it stays still. "Read the label" shows the frosted end alone, large.
import { lazy, Suspense, useMemo, useRef, useState, type PointerEvent } from "react";
import { api } from "../api/client";
import { useRoom } from "../design/theme";
import { hasWebGL, roomColour } from "../glass/GlassSet";
import type { GlassItem } from "../glass/model";
import { useResource } from "../api/useResource";
import { useI18n } from "../i18n";
import { Skeleton } from "../ui/Feedback";
import styles from "./SlideObject.module.css";

const MAX_TILT = 5;

/** The drawing cropped to its frosted end, with its ids renamed so it can share the page with the whole slide. */
export function labelOnly(svg: string, slideId: string): string {
  const width = /data-label-mm="([\d.]+)"/.exec(svg)?.[1];
  const height = /viewBox="0 0 [\d.]+ ([\d.]+)"/.exec(svg)?.[1];
  const short = /data-format="[\d.]+x([\d.]+)"/.exec(svg)?.[1];
  if (!width || !height || !short) return svg;
  return svg
    .replaceAll(`${slideId}-`, `${slideId}-label-`)
    .replace(/viewBox="0 0 [\d.]+ [\d.]+"/, `viewBox="0 0 ${width} ${short}"`)
    .replace(/ width="[\d.]+mm" height="[\d.]+mm"/, "");
}

export function useSlideSvg(slideId: string) {
  const { lang } = useI18n();
  return useResource(`slide-svg:${slideId}:${lang}`, (signal) => api.slideSvg(slideId, lang, signal));
}

const GlassScene = lazy(() => import("../glass/GlassScene"));

/** The slide on its own place: real glass in 3D where the device draws WebGL (the same glass slide as every set,
 * with its QR), the server's drawing otherwise, and while the 3D code loads. */
export function SlideObject({ slideId, item }: { slideId: string; item?: GlassItem | null }) {
  const drawn = useMemo(hasWebGL, []);
  const { room } = useRoom();
  const still = typeof window !== "undefined" && Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
  const colours = useMemo(() => ({ accent: roomColour("--c-focus", "#0056aa"), ground: roomColour("--c-bg", "#f9f5ee") }),
    // The room decides the colours.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [room]);
  if (!drawn || !item) return <SlideDrawing slideId={slideId} />;
  return (
    <div className={styles.glass} data-testid="slide-object" data-drawn="3d">
      <Suspense fallback={<SlideDrawing slideId={slideId} />}>
        <GlassScene items={[item]} arrangement="carousel" selected={0} onSelect={() => undefined}
          onOpen={() => undefined} still={still} title={item.name} hue={item.hue} accent={colours.accent}
          ground={colours.ground} onSpots={() => undefined} closeUp />
      </Suspense>
    </div>
  );
}

/** The server's drawing of the slide, inlined: its colours follow the room. */
function SlideDrawing({ slideId }: { slideId: string }) {
  const { t } = useI18n();
  const svg = useSlideSvg(slideId);
  const frame = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const still = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  const follow = (e: PointerEvent<HTMLDivElement>) => {
    if (still || e.pointerType !== "mouse" || !frame.current) return;
    const box = frame.current.getBoundingClientRect();
    const dx = (e.clientX - box.left) / box.width - 0.5;
    const dy = (e.clientY - box.top) / box.height - 0.5;
    setTilt({ x: -dy * MAX_TILT * 2, y: dx * MAX_TILT * 2 });
  };

  if (!svg.value) {
    return svg.state === "error" ? <p role="alert">{t("slide.drawing.error")}</p> : <Skeleton lines={3} />;
  }
  return (
    <div ref={frame} className={styles.frame} onPointerMove={follow} onPointerLeave={() => setTilt({ x: 0, y: 0 })}>
      <div className={styles.object} style={{ transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)` }}
        data-testid="slide-object" dangerouslySetInnerHTML={{ __html: svg.value }} />
    </div>
  );
}

export function LabelReading({ slideId }: { slideId: string }) {
  const svg = useSlideSvg(slideId);
  if (!svg.value) return <Skeleton lines={2} />;
  return <div className={styles.reading} dangerouslySetInnerHTML={{ __html: labelOnly(svg.value, slideId) }} />;
}
