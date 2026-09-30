// A set of glass slides as the page shows it (U17): the arrangement the visitor chose (kept on this device, the same
// for every set of the page), the 3D stage, the chosen slide's caption with its way in, and an accessible layer over
// the stage, after the W3C carousel pattern: a labelled group of slides, previous and next buttons that do not move
// focus, the arrow keys, Home and End to move, Enter to open. Every slide of the layer is a real link, and its place
// on the stage is written on it, so a pointer (or a gate) reaches the same slide the eye sees. Nothing turns by itself.
import {
  lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type KeyboardEvent,
  type PointerEvent,
} from "react";
import { Link, useLocation } from "wouter";
import { useRoom } from "../design/theme";
import { useI18n } from "../i18n";
import type { MessageKey } from "../i18n/en";
import { IconButton } from "../ui/Button";
import { Glyph } from "../ui/Icon";
import { FlatGlassSlide } from "./FlatGlassSlide";
import type { ScreenSpot } from "./GlassScene";
import { trayReference } from "../slide/names";
import { ARRANGEMENTS, FOLDER_PLACES, folderPages, stepFromKey, type Arrangement, type GlassItem } from "./model";
import styles from "./GlassSet.module.css";

const GlassScene = lazy(() => import("./GlassScene"));
const STORAGE_KEY = "laminario.arrangement";
const CHANGED = "laminario:arrangement";
const GLYPHS: Record<Arrangement, string> = { carousel: "carousel", drawer: "cabinet", box: "box", folder: "folder" };

function storedArrangement(): Arrangement {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return (ARRANGEMENTS as readonly string[]).includes(value ?? "") ? (value as Arrangement) : "carousel";
  } catch {
    return "carousel";
  }
}

/** The arrangement the visitor chose, the same for every set of the page, kept on this device. */
export function useArrangement(): [Arrangement, (next: Arrangement) => void] {
  const [value, setValue] = useState<Arrangement>(storedArrangement);
  useEffect(() => {
    const follow = () => setValue(storedArrangement());
    window.addEventListener(CHANGED, follow);
    return () => window.removeEventListener(CHANGED, follow);
  }, []);
  const choose = useCallback((next: Arrangement) => {
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage may be refused (a private window): the choice holds for this page.
    }
    setValue(next);
    window.dispatchEvent(new Event(CHANGED));
  }, []);
  return [value, choose];
}

let webgl: boolean | null = null;

/** Whether this device draws WebGL; without it the slides are drawn flat. */
export function hasWebGL(): boolean {
  if (webgl !== null) return webgl;
  try {
    const canvas = document.createElement("canvas");
    webgl = Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    webgl = false;
  }
  return webgl;
}

function useStill(): boolean {
  const query = "(prefers-reduced-motion: reduce)";
  const [still, setStill] = useState(() => typeof window !== "undefined" && Boolean(window.matchMedia?.(query).matches));
  useEffect(() => {
    const list = window.matchMedia?.(query);
    if (!list) return undefined;
    const follow = () => setStill(list.matches);
    list.addEventListener("change", follow);
    return () => list.removeEventListener("change", follow);
  }, []);
  return still;
}

/** A colour of the room, read from the page's tokens (the scene paints with resolved colours). */
export function roomColour(token: string, fallback = "#8e5318"): string {
  if (typeof document === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(token).trim();
  return value || fallback;
}

export interface GlassSetProps {
  items: GlassItem[];
  /** The set's accessible name ("The collections of Life"). */
  label: string;
  /** The words on the drawer's label holder, the box's index sheet, the folder's cover. */
  title: string;
  /** The token of the set's hue ("--h-plants"). */
  hue?: string;
  /** The slide chosen first (the current node, when the set holds it). */
  initial?: number;
  /** A test hook and a way for the page to name the set. */
  name?: string;
}

export function GlassSet({ items, label, title, hue = "--c-accent", initial = 0, name }: GlassSetProps) {
  const { t } = useI18n();
  const { room } = useRoom();
  const [, navigate] = useLocation();
  const [arrangement, setArrangement] = useArrangement();
  const [selected, setSelected] = useState(() => Math.max(0, Math.min(initial, items.length - 1)));
  const [spots, setSpots] = useState<(ScreenSpot | null)[]>([]);
  const [focus, setFocus] = useState<number | null>(null);
  const still = useStill();
  const drawn = useMemo(hasWebGL, []);
  const links = useRef<(HTMLAnchorElement | null)[]>([]);
  const drag = useRef<{ x: number } | null>(null);

  const colours = useMemo(() => ({ hue: roomColour(hue), accent: roomColour("--c-focus", "#0056aa"),
    ground: roomColour("--c-bg", "#f9f5ee") }),
    // The room decides the colours.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [hue, room]);

  useEffect(() => {
    setSelected((s) => Math.max(0, Math.min(s, items.length - 1)));
  }, [items.length]);

  const choose = useCallback((index: number, moveFocus = false) => {
    setSelected(index);
    if (moveFocus) links.current[index]?.focus({ preventScroll: true });
  }, []);
  const open = useCallback((index: number) => {
    const item = items[index];
    if (item) navigate(item.href);
  }, [items, navigate]);

  const onKey = (e: KeyboardEvent<HTMLElement>) => {
    const next = stepFromKey(e.key, selected, items.length);
    if (next === null) return;
    e.preventDefault();
    choose(next, true);
  };

  // A drag across the carousel turns it, a slide per 70 pixels.
  const down = (e: PointerEvent<HTMLDivElement>) => {
    if (arrangement === "carousel") drag.current = { x: e.clientX };
  };
  const move = (e: PointerEvent<HTMLDivElement>) => {
    if (!drag.current) return;
    const dx = e.clientX - drag.current.x;
    if (Math.abs(dx) >= 70) {
      drag.current.x = e.clientX;
      setSelected((s) => Math.max(0, Math.min(items.length - 1, s - Math.sign(dx))));
    }
  };
  const up = () => { drag.current = null; };

  if (!items.length) return null;
  const chosen = items[selected] ?? items[0];
  const ring = focus !== null ? spots[focus] : null;
  const page = Math.floor(selected / FOLDER_PLACES);

  return (
    <section className={styles.set} aria-roledescription="carousel" aria-label={label} data-glass-set={name ?? label}
      data-arrangement={arrangement} data-drawn={drawn ? "3d" : "flat"} onKeyDown={onKey}>
      <div className={styles.bar}>
        <div className={styles.arrangements} role="radiogroup" aria-label={t("glass.arrangement")}>
          {ARRANGEMENTS.map((a) => (
            <button key={a} type="button" role="radio" aria-checked={a === arrangement} className={styles.arrangement}
              onClick={() => setArrangement(a)} title={t(`glass.${a}` as MessageKey)}>
              <Glyph name={GLYPHS[a]} size={20} />
              <span className={styles.arrangementName}>{t(`glass.${a}` as MessageKey)}</span>
            </button>
          ))}
        </div>
        <div className={styles.steps}>
          <IconButton icon="chevron-left" label={t("glass.previous")} disabled={selected === 0}
            onClick={() => choose(selected - 1)} />
          <span className={styles.position} aria-live="polite">
            {arrangement === "folder" && items.length > FOLDER_PLACES
              ? t("glass.page", { page: page + 1, pages: folderPages(items.length) })
              : t("glass.position", { n: selected + 1, total: items.length })}
          </span>
          <IconButton icon="chevron-right" label={t("glass.next")} disabled={selected >= items.length - 1}
            onClick={() => choose(selected + 1)} />
        </div>
      </div>

      <div className={[styles.stage, styles[arrangement]].join(" ")} onPointerDown={down} onPointerMove={move}
        onPointerUp={up} onPointerLeave={up} data-glass-stage="">
        {drawn ? (
          <Suspense fallback={<Flat items={items} selected={selected} />}>
            <GlassScene items={items} arrangement={arrangement} selected={selected} onSelect={(i) => choose(i)}
              onOpen={open} still={still} title={title} hue={colours.hue} accent={colours.accent} ground={colours.ground}
              onSpots={setSpots} />
          </Suspense>
        ) : (
          <>
            <p className={styles.flatNote}>{t("glass.flat")}</p>
            <Flat items={items} selected={selected} />
          </>
        )}
        {ring ? (
          <span className={styles.ring} aria-hidden="true" style={{ left: ring.left - 4, top: ring.top - 4,
            width: ring.width + 8, height: ring.height + 8 } as CSSProperties} />
        ) : null}
      </div>

      <p className={styles.caption}>
        <span className={[styles.captionName, chosen.italic ? styles.italic : ""].join(" ")}>{chosen.name}</span>
        {chosen.facts.length ? <span className={styles.captionFacts}>{chosen.facts.join(" · ")}</span> : null}
        <Link href={chosen.href} className={styles.open}>{t("glass.open")}<Glyph name="chevron-right" size={16} /></Link>
      </p>

      <ul className={styles.layer} aria-live="off">
        {items.map((item, i) => {
          const spot = spots[i];
          return (
            <li key={item.id} role="group" aria-roledescription="slide"
              aria-label={t("glass.position", { n: i + 1, total: items.length })}>
              <Link href={item.href} ref={(el: HTMLAnchorElement | null) => { links.current[i] = el; }}
                tabIndex={i === selected ? 0 : -1} className={styles.layerLink}
                data-glass-item={item.id} data-pick-x={spot ? Math.round(spot.pickX) : undefined}
                data-pick-y={spot ? Math.round(spot.pickY) : undefined}
                onFocus={() => { setFocus(i); setSelected(i); }} onBlur={() => setFocus(null)}>
                {item.description ?? [item.name, ...item.facts].join(", ")}
              </Link>
            </li>
          );
        })}
      </ul>
      <p className={styles.keys}>{t("glass.keys")}</p>
    </section>
  );
}

/** The slides drawn flat, at one scale for the whole set: each as long as its format against the set's longest
 * (R-1007). */
function Flat({ items, selected }: { items: GlassItem[]; selected: number }) {
  const ref = trayReference(items.map((i) => ({ width_mm: i.format.long, height_mm: i.format.short })));
  return (
    <ul className={styles.flat}>
      {items.map((item, i) => (
        <li key={item.id} style={{ "--share": item.format.long / ref } as CSSProperties}>
          <FlatGlassSlide item={item} current={i === selected} />
        </li>
      ))}
    </ul>
  );
}
