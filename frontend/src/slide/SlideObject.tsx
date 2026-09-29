// The slide as an object: the server's drawing in millimetres (R-1101), inlined so it takes the room's colours and the
// page's label face. The glass follows the pointer a few degrees, as a slide tilted in the hand catches the light;
// with reduced motion it stays still. "Read the label" shows the frosted end alone, large.
import { useRef, useState, type PointerEvent } from "react";
import { api } from "../api/client";
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

export function SlideObject({ slideId }: { slideId: string }) {
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
