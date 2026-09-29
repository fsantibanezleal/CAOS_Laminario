// Calibrate a pixel size on a stage micrometer (R-1207). The contributor opens a photograph of the micrometer taken
// with the same camera and objective (it stays on this device), marks both ends of a known length, and gives that
// length; the pixel size is d / n with its uncertainty of one pixel at each end, 2p / n. The ends are placed by a click
// (a third click starts again), moved one pixel at a time with the arrow keys, or typed as coordinates, so the mouse
// is never the only way. The photograph is drawn at its own pixels in a scrolling frame, zoomable, since a click on a
// shrunken picture cannot be closer than the pixels it hides.
import { useEffect, useRef, useState, type KeyboardEvent, type MouseEvent } from "react";
import { calibrate, LENGTH_UNITS, withinRange, written, type Calibration, type LengthUnit,
  type Point } from "../../contribute/calibration";
import { useI18n } from "../../i18n";
import { Button, IconButton } from "../../ui/Button";
import { Select, TextField } from "../../ui/Field";
import styles from "./Contribute.module.css";

const ZOOMS = [0.25, 0.5, 1, 2, 4] as const;

export function Calibrator({ onUse, onClose }: { onUse: (c: Calibration) => void; onClose: () => void }) {
  const { t } = useI18n();
  const dialog = useRef<HTMLDialogElement>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  const [zoom, setZoom] = useState<number>(1);
  const [points, setPoints] = useState<Point[]>([]);
  const [selected, setSelected] = useState(0);
  const [length, setLength] = useState("100");
  const [unit, setUnit] = useState<LengthUnit>("um");

  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);

  const result = points.length === 2
    ? calibrate(points[0], points[1], Number(length.replace(",", ".")), unit) : null;
  const shown = result ? written(result) : null;

  const place = (e: MouseEvent<HTMLDivElement>) => {
    if (!natural) return;
    const box = e.currentTarget.getBoundingClientRect();
    const p = { x: Math.round((e.clientX - box.left) / zoom), y: Math.round((e.clientY - box.top) / zoom) };
    setPoints((list) => (list.length >= 2 ? [p] : [...list, p]));
    setSelected(points.length >= 2 ? 0 : points.length);
  };

  const nudge = (e: KeyboardEvent<HTMLDivElement>) => {
    const step = e.shiftKey ? 10 : 1;
    const move: Record<string, [number, number]> = { ArrowLeft: [-step, 0], ArrowRight: [step, 0],
      ArrowUp: [0, -step], ArrowDown: [0, step] };
    const d = move[e.key];
    if (d && points[selected]) {
      e.preventDefault();
      setPoints((list) => list.map((p, i) => (i === selected ? { x: p.x + d[0], y: p.y + d[1] } : p)));
    } else if (e.key === "Tab" && points.length === 2 && !e.shiftKey && selected === 0) {
      e.preventDefault();
      setSelected(1);
    }
  };

  const setCoordinate = (i: number, axis: "x" | "y", value: string) => {
    const n = Number(value);
    if (!Number.isFinite(n)) return;
    setPoints((list) => {
      const next = [...list];
      while (next.length <= i) next.push({ x: 0, y: 0 });
      next[i] = { ...next[i], [axis]: n };
      return next;
    });
  };

  return (
    <dialog ref={dialog} className={`${styles.dialog} ${styles.calibrator}`} onClose={onClose}
      aria-labelledby="calibrate-title">
      <div className={styles.dialogBody}>
        <div className={styles.dialogHead}>
          <h2 id="calibrate-title">{t("calibrate.title")}</h2>
          <IconButton icon="close" label={t("action.close")} onClick={() => dialog.current?.close()} />
        </div>
        <p className={styles.fieldHint}>{t("calibrate.lead")}</p>
        <label className={styles.fileButton}>
          <input type="file" accept="image/*" onChange={(e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            if (url) URL.revokeObjectURL(url);
            setUrl(URL.createObjectURL(file));
            setPoints([]);
            setNatural(null);
          }} />
          <span>{url ? t("calibrate.another") : t("calibrate.choose")}</span>
        </label>

        {url ? (
          <>
            <div className={styles.zoomRow} role="group" aria-label={t("calibrate.zoom")}>
              {ZOOMS.map((z) => (
                <button key={z} type="button" className={styles.zoomButton} aria-pressed={zoom === z}
                  onClick={() => setZoom(z)}>{`${z * 100}%`}</button>
              ))}
            </div>
            <div className={styles.calibrationFrame}>
              <div className={styles.calibrationImage} tabIndex={0} role="application"
                aria-label={t("calibrate.canvas")} aria-describedby="calibrate-keys" onClick={place} onKeyDown={nudge}
                style={natural ? { width: natural.w * zoom, height: natural.h * zoom } : undefined}>
                <img src={url} alt="" draggable={false} onLoad={(e) => setNatural({ w: e.currentTarget.naturalWidth,
                  h: e.currentTarget.naturalHeight })} style={natural ? { width: natural.w * zoom } : undefined} />
                {natural ? (
                  <svg className={styles.calibrationMarks} viewBox={`0 0 ${natural.w} ${natural.h}`}
                    width={natural.w * zoom} height={natural.h * zoom} aria-hidden="true">
                    {points.length === 2 ? <line x1={points[0].x} y1={points[0].y} x2={points[1].x} y2={points[1].y}
                      className={styles.calibrationLine} style={{ strokeWidth: 2 / zoom }} /> : null}
                    {points.map((p, i) => (
                      <g key={i} className={i === selected ? styles.markSelected : styles.mark}>
                        <line x1={p.x - 12 / zoom} y1={p.y} x2={p.x + 12 / zoom} y2={p.y} style={{ strokeWidth: 1.5 / zoom }} />
                        <line x1={p.x} y1={p.y - 12 / zoom} x2={p.x} y2={p.y + 12 / zoom} style={{ strokeWidth: 1.5 / zoom }} />
                      </g>
                    ))}
                  </svg>
                ) : null}
              </div>
            </div>
            <p id="calibrate-keys" className={styles.fieldHint}>{t("calibrate.keys")}</p>
          </>
        ) : null}

        <div className={styles.grid4}>
          {[0, 1].map((i) => (["x", "y"] as const).map((axis) => (
            <TextField key={`${i}${axis}`} label={t("calibrate.point", { which: i === 0 ? "A" : "B", axis })}
              inputMode="numeric" value={points[i] ? String(points[i][axis]) : ""}
              onChange={(e) => setCoordinate(i, axis, e.target.value)} />
          )))}
        </div>
        <div className={styles.grid2}>
          <TextField label={t("calibrate.length")} value={length} inputMode="decimal" hint={t("calibrate.length.hint")}
            onChange={(e) => setLength(e.target.value)} />
          <Select label={t("calibrate.unit")} value={unit} onChange={(e) => setUnit(e.target.value as LengthUnit)}
            options={(Object.keys(LENGTH_UNITS) as LengthUnit[]).map((u) => ({ value: u, label: t(`unit.${u}`) }))} />
        </div>

        <div className={styles.calibrationResult} role="status" aria-live="polite">
          {result && shown ? (
            <>
              <p className={styles.resultValue}>{t("calibrate.result", { value: shown.value,
                uncertainty: shown.uncertainty })}</p>
              <p className={styles.fieldHint}>{t("calibrate.detail", { pixels: result.pixels.toFixed(1),
                length: result.length, relative: ((2 / result.pixels) * 100).toFixed(2) })}</p>
              {!withinRange(result.pixelSize) ? <p className={styles.fieldError}>{t("calibrate.outOfRange")}</p> : null}
              {2 / result.pixels > 0.01 ? <p className={styles.flagText}>{t("calibrate.short")}</p> : null}
            </>
          ) : <p className={styles.fieldHint}>{t("calibrate.waiting")}</p>}
        </div>

        <div className={styles.dialogActions}>
          <Button onClick={() => dialog.current?.close()}>{t("action.cancel")}</Button>
          <Button variant="primary" icon="check" disabled={!result || !withinRange(result.pixelSize)}
            onClick={() => result && onUse(result)}>{t("calibrate.use")}</Button>
        </div>
      </div>
    </dialog>
  );
}
