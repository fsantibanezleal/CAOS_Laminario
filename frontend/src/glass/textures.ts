// What is painted on the glass: the node's icon (from the tree's sprite), the frosted labels with their writing (in the
// page's own faces, which are woff2 files a WebGL text renderer cannot read, so the labels are drawn on a canvas), and
// the specimen's image or the slide's photograph. The labels are typed in the label face, as the tray's are. Every texture is made once per content and kept.
import * as THREE from "three";
import { coverslipSide, type GlassItem, type SlideFormat } from "./model";

/** Pixels per millimetre of a label's canvas: sharp at a slide's size in the scene, small enough for 40 slides. */
const PX_PER_MM = 14;
/** The writing on a label: a slide label's ink, whatever the room (the glass is the same glass by lamplight). */
const INK = "#251c16";
const INK_MUTED = "#5e554d";

let sprite: Promise<Document> | null = null;

function spriteDocument(): Promise<Document> {
  sprite ??= fetch("/icons.svg")
    .then((r) => r.text())
    .then((text) => new DOMParser().parseFromString(text, "image/svg+xml"));
  return sprite;
}

/** A standalone SVG of one sprite symbol, stroked in ``colour``: what ``<use>`` shows in the page, as a file. */
export function symbolSvg(doc: Document, id: string, colour: string, size = 512): string | null {
  const symbol = Array.from(doc.getElementsByTagName("symbol")).find((s) => s.getAttribute("id") === id);
  if (!symbol) return null;
  const attributes = ["fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"]
    .map((a) => (symbol.getAttribute(a) ? ` ${a}="${symbol.getAttribute(a)}"` : "")).join("");
  const body = Array.from(symbol.childNodes)
    .filter((n) => !(n.nodeType === 1 && (n as Element).tagName.toLowerCase() === "title"))
    .map((n) => new XMLSerializer().serializeToString(n)).join("")
    .replace(/ xmlns="http:\/\/www\.w3\.org\/2000\/svg"/g, "");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${symbol.getAttribute("viewBox") ?? "0 0 32 32"}" `
    + `width="${size}" height="${size}" color="${colour}"${attributes}>${body}</svg>`;
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.decoding = "async";
    image.crossOrigin = "anonymous";
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`cannot load ${src}`));
    image.src = src;
  });
}

const icons = new Map<string, Promise<THREE.Texture | null>>();

/** The node's icon as a texture, stroked in its collection's hue on transparent ground. */
export function iconTexture(id: string, colour: string): Promise<THREE.Texture | null> {
  const key = `${id}|${colour}`;
  let found = icons.get(key);
  if (!found) {
    found = spriteDocument().then(async (doc) => {
      const svg = symbolSvg(doc, id, colour) ?? symbolSvg(doc, id.split(".").slice(0, 2).join("."), colour);
      if (!svg) return null;
      const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
      try {
        const image = await loadImage(url);
        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = 512;
        canvas.getContext("2d")?.drawImage(image, 0, 0, 512, 512);
        const texture = new THREE.CanvasTexture(canvas);
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.anisotropy = 4;
        return texture;
      } finally {
        URL.revokeObjectURL(url);
      }
    }).catch(() => null);
    icons.set(key, found);
  }
  return found;
}

const pictures = new Map<string, Promise<THREE.Texture | null>>();

/** An image (a specimen's thumbnail, a slide's photograph) as a texture, cropped to fill ``aspect`` (width over
 * height) around its centre, as the glass shows it. */
export function pictureTexture(src: string, aspect: number): Promise<THREE.Texture | null> {
  const key = `${src}|${aspect.toFixed(3)}`;
  let found = pictures.get(key);
  if (!found) {
    found = loadImage(src).then((image) => {
      const texture = new THREE.Texture(image);
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = 4;
      const own = image.naturalWidth / Math.max(1, image.naturalHeight);
      if (own > aspect) {
        texture.repeat.set(aspect / own, 1);
        texture.offset.set((1 - aspect / own) / 2, 0);
      } else {
        texture.repeat.set(1, own / aspect);
        texture.offset.set(0, (1 - own / aspect) / 2);
      }
      texture.needsUpdate = true;
      return texture;
    }).catch(() => null);
    pictures.set(key, found);
  }
  return found;
}

/** The frosted end's ground: fine grain, as ground glass scatters light. Seeded, so every label is the same glass. */
function frost(ctx: CanvasRenderingContext2D, w: number, h: number) {
  ctx.fillStyle = "rgba(247, 247, 243, 0.94)";
  ctx.fillRect(0, 0, w, h);
  let seed = 7;
  const next = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < (w * h) / 9; i += 1) {
    ctx.fillStyle = next() > 0.5 ? "rgba(255,255,255,0.35)" : "rgba(200,204,200,0.28)";
    ctx.fillRect(next() * w, next() * h, 1.2, 1.2);
  }
}

/** Lines of ``text`` that fit ``width``, breaking at spaces, at most ``max`` lines (the last one shortened). */
export function wrap(measure: (s: string) => number, text: string, width: number, max: number): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let line = "";
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (measure(next) <= width || !line) line = next;
    else {
      lines.push(line);
      line = word;
    }
  }
  if (line) lines.push(line);
  if (lines.length <= max) return lines;
  const kept = lines.slice(0, max);
  let last = kept[max - 1];
  while (last.length > 1 && measure(`${last}…`) > width) last = last.slice(0, -1);
  kept[max - 1] = `${last.trimEnd()}…`;
  return kept;
}

export interface LabelSides {
  left: THREE.CanvasTexture;
  right: THREE.CanvasTexture;
}

/** The two frosted ends, written: the name at the left end (with the collection's band and the reference), the facts
 * at the right end, as a slide is labelled. The canvas is portrait: the label is read across the slide's short side. */
export function labelTextures(item: GlassItem, format: SlideFormat): LabelSides {
  const w = Math.round(format.label * PX_PER_MM);
  const h = Math.round(format.short * PX_PER_MM);
  const mm = PX_PER_MM;
  const make = () => {
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    return canvas;
  };

  const left = make();
  const l = left.getContext("2d");
  if (l) {
    frost(l, w, h);
    l.fillStyle = item.hue;
    l.fillRect(0, 0, w, 2.6 * mm);
    const pad = 1.4 * mm;
    let y = 2.6 * mm + 1.6 * mm;
    l.fillStyle = INK;
    l.textBaseline = "top";
    const size = 2.9 * mm;
    l.font = `${item.italic ? "italic " : ""}700 ${size}px "Courier Prime", "Courier New", monospace`;
    for (const line of wrap((s) => l.measureText(s).width, item.name, w - 2 * pad, 5)) {
      l.fillText(line, pad, y);
      y += size * 1.12;
    }
    if (item.reference) {
      y += 0.8 * mm;
      l.fillStyle = INK_MUTED;
      const small = 2.1 * mm;
      l.font = `400 ${small}px "Courier Prime", "Courier New", monospace`;
      for (const line of wrap((s) => l.measureText(s).width, item.reference, w - 2 * pad, 2)) {
        l.fillText(line, pad, y);
        y += small * 1.15;
      }
    }
  }

  const right = make();
  const r = right.getContext("2d");
  if (r) {
    frost(r, w, h);
    const pad = 1.4 * mm;
    let y = 2.2 * mm;
    r.textBaseline = "top";
    r.fillStyle = INK;
    const size = 2.2 * mm;
    r.font = `400 ${size}px "Courier Prime", "Courier New", monospace`;
    const lines = item.qr ? 3 : 5;
    for (const fact of item.facts.slice(0, lines)) {
      for (const line of wrap((s) => r.measureText(s).width, fact, w - 2 * pad, 2)) {
        r.fillText(line, pad, y);
        y += size * 1.18;
      }
      y += 0.6 * mm;
    }
    if (item.qr) {
      // The slide's own QR, as the server draws it on the label, at the foot of the right end with its quiet zone.
      const side = Math.min(w - 2 * pad, h - y - pad);
      const scale = side / item.qr.size;
      r.save();
      r.fillStyle = "#ffffff";
      r.fillRect(w - pad - side - 0.4 * mm, h - pad - side - 0.4 * mm, side + 0.8 * mm, side + 0.8 * mm);
      r.translate(w - pad - side, h - pad - side);
      r.scale(scale, scale);
      r.translate(-item.qr.x, -item.qr.y);
      r.fillStyle = INK;
      r.fill(new Path2D(item.qr.d));
      r.restore();
    }
  }

  const texture = (canvas: HTMLCanvasElement) => {
    const t = new THREE.CanvasTexture(canvas);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 4;
    return t;
  };
  return { left: texture(left), right: texture(right) };
}

/** The faces the labels are written in, loaded before any label is drawn (a canvas does not wait for a web font). */
export function labelFacesReady(): Promise<unknown> {
  if (typeof document === "undefined" || !document.fonts) return Promise.resolve();
  return Promise.all([
    document.fonts.load('700 40px "Courier Prime"'),
    document.fonts.load('italic 700 40px "Courier Prime"'),
    document.fonts.load('400 30px "Courier Prime"'),
  ]).catch(() => undefined);
}

/** The sample area's side for a slide, for the textures that fill it. */
export const sampleSide = coverslipSide;
