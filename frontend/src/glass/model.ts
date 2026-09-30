// The glass slide, the one object of the interface (U17): what a slide carries and where each slide of a set lies in
// the arrangement the visitor chose. Pure functions, so the layouts are tested without a canvas.
//
// Units are millimetres, as the object is: a standard slide is 76 x 26 x 1 mm (ISO 8037-1), its frosted marking end
// 20 mm long, a coverslip 0.17 mm thick (ISO 8255-1). The scene's origin is the arrangement's centre; +y is up, the
// camera looks toward -z.

/** One glass slide of a set: a realm, a collection, a drawer, a specimen slide, or any other content. */
export interface GlassItem {
  id: string;
  /** Where opening the slide goes. */
  href: string;
  /** Written on the frosted label at the left end, as a slide's name is. */
  name: string;
  /** Whether the name is set in italic (a taxon at genus rank or below). */
  italic?: boolean;
  /** A catalogue number or identifier, under the name. */
  reference?: string;
  /** Written on the label at the right end: counts, a place, a date. */
  facts: string[];
  /** The sprite symbol drawn in the sample area (realms, collections, drawers, and slides without an image). */
  icon?: string;
  /** The specimen's image, seen under the coverslip. */
  image?: string | null;
  /** A photograph of the whole glass slide: the slide is shown as that photograph, its real glass. */
  photo?: string | null;
  /** The colour of the label's band: the collection's hue. */
  hue: string;
  /** The slide's own size, long and short side and marking end, in millimetres. */
  format: SlideFormat;
  /** A slide that holds nothing yet (an empty drawer): drawn fainter. */
  empty?: boolean;
  /** The words a screen reader says for the slide, when they differ from its name and facts. */
  description?: string;
}

export interface SlideFormat {
  long: number;
  short: number;
  label: number;
}

/** The standard slide: 76 x 26 mm with a 20 mm frosted end. */
export const STANDARD: SlideFormat = { long: 76, short: 26, label: 20 };
/** The glass is 1 mm thick; a coverslip 0.17 mm. */
export const GLASS_MM = 1;
export const COVERSLIP_MM = 0.17;

/** The ways a set of slides can be laid out; the visitor chooses one and it is kept on this device. */
export const ARRANGEMENTS = ["carousel", "drawer", "box", "folder"] as const;
export type Arrangement = (typeof ARRANGEMENTS)[number];

export interface Placement {
  position: [number, number, number];
  rotation: [number, number, number];
  /** Hidden slides are not drawn (a folder shows one page of 20). */
  visible: boolean;
}

/** Slides a folder holds, as the 20-place cardboard folders do (2 columns of 10 recesses). */
export const FOLDER_PLACES = 20;
/** Rows of a slide box: 2 rows of slots, as a 100-place box holds them. */
export const BOX_ROWS = 2;
/** The pitch of the slots of a box and of a filing drawer as drawn: real slots are about 3 mm apart; drawn at 7 mm, the
 * top strip of every slide shows above the one in front, where a hand would find it. */
export const SLOT_MM = 7;
/** How far a slide rises out of a drawer or a box when it is chosen, clear of its neighbours, to read its label. */
export const LIFT_MM = 30;
/** Slides on a carousel lean back a little, as on a stand, so their edges catch the light. */
export const LEAN = -7 * (Math.PI / 180);

const DEG = Math.PI / 180;

/** The coverslip's side on a slide: square, 22 mm on a standard slide, never wider than the space between the ends. */
export function coverslipSide(format: SlideFormat): number {
  return Math.min(22, format.short - 3, format.long - 2 * format.label - 3);
}

/** The carousel's ring: slides stand upright around it, the chosen one in front, facing the visitor. */
export function carouselRing(n: number): { step: number; radius: number } {
  // Neighbours stand far enough apart that their 76 mm do not touch: the chord between them is at least 86 mm.
  const step = Math.min((2 * Math.PI) / Math.max(n, 1), 0.62);
  const radius = Math.max(80, 43 / Math.sin(step / 2));
  return { step, radius };
}

/** Where every slide of a set of ``n`` lies, the chosen one ``selected`` (and a lifted one, where it rises). */
export function layout(arrangement: Arrangement, n: number, selected: number, lifted: number | null = null):
  Placement[] {
  const out: Placement[] = [];
  const s = Math.max(0, Math.min(selected, n - 1));
  if (arrangement === "carousel") {
    const { step, radius } = carouselRing(n);
    for (let i = 0; i < n; i += 1) {
      // The ring turns so the chosen slide is in front; the others go round, the far side hidden behind.
      let a = (i - s) * step;
      if (n * step >= 2 * Math.PI - 1e-6) a = ((a + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
      const front = Math.abs(a) < Math.PI / 2 + 0.2;
      out.push({ position: [radius * Math.sin(a), 0, radius * Math.cos(a) - radius], rotation: [LEAN, a, 0],
        visible: front });
    }
    return out;
  }
  if (arrangement === "drawer" || arrangement === "box") {
    // Slides stand on their long edge, faces toward the visitor, one behind the other; a box keeps them in two
    // rows side by side. The chosen slide rises out of its slot to show its label.
    const rows = arrangement === "box" ? BOX_ROWS : 1;
    const perRow = Math.ceil(n / rows);
    for (let i = 0; i < n; i += 1) {
      const row = Math.floor(i / perRow);
      const k = i % perRow;
      const x = rows === 1 ? 0 : (row - (rows - 1) / 2) * 84;
      const z = -(k - (perRow - 1) / 2) * SLOT_MM;
      const up = i === (lifted ?? s) ? LIFT_MM : 0;
      // Standing slides lean a little back, as they do against the drawer's backstop.
      out.push({ position: [x, up, z], rotation: [-8 * DEG, 0, 0], visible: true });
    }
    return out;
  }
  // A folder: 20 recesses in 2 columns of 10, slides lying flat; the page holding the chosen slide is shown.
  const page = Math.floor(s / FOLDER_PLACES);
  for (let i = 0; i < n; i += 1) {
    const k = i - page * FOLDER_PLACES;
    const col = Math.floor(k / 10);
    const row = k % 10;
    const up = i === (lifted ?? s) ? 6 : 0;
    out.push({ position: [(col - 0.5) * 86, up, (row - 4.5) * 30], rotation: [-Math.PI / 2, 0, 0],
      visible: k >= 0 && k < FOLDER_PLACES });
  }
  return out;
}

/** The pages a folder arrangement needs for ``n`` slides. */
export function folderPages(n: number): number {
  return Math.max(1, Math.ceil(n / FOLDER_PLACES));
}

/** Where the camera stands for an arrangement: its position and the point it looks at, in millimetres. */
export function cameraFor(arrangement: Arrangement, n: number): { position: [number, number, number];
  target: [number, number, number]; fov: number } {
  if (arrangement === "carousel") return { position: [0, 16, 118], target: [0, -1, -6], fov: 38 };
  if (arrangement === "drawer") {
    const depth = Math.max(40, n * SLOT_MM);
    return { position: [0, 78 + depth * 0.45, 92 + depth * 0.7], target: [0, 10, -depth * 0.12], fov: 40 };
  }
  if (arrangement === "box") {
    const depth = Math.max(40, Math.ceil(n / BOX_ROWS) * SLOT_MM);
    return { position: [0, 92 + depth * 0.4, 118 + depth * 0.55], target: [0, 8, -depth * 0.05], fov: 42 };
  }
  return { position: [0, 330, 170], target: [0, 0, 5], fov: 42 };
}

/** The next slide to choose from a key: the arrow keys and Home and End move through the set. */
export function stepFromKey(key: string, current: number, n: number): number | null {
  if (n === 0) return null;
  if (key === "ArrowRight" || key === "ArrowDown") return Math.min(n - 1, current + 1);
  if (key === "ArrowLeft" || key === "ArrowUp") return Math.max(0, current - 1);
  if (key === "Home") return 0;
  if (key === "End") return n - 1;
  if (key === "PageDown") return Math.min(n - 1, current + FOLDER_PLACES);
  if (key === "PageUp") return Math.max(0, current - FOLDER_PLACES);
  return null;
}

/** How many slides on each side of the chosen one the scene draws: a set of hundreds (a search grown page by page)
 * is drawn around where the visitor is; the page's accessible layer still lists every slide. */
export const DRAWN_SPAN = 40;

/** The indexes the scene draws for a set of ``n`` with ``selected`` chosen: a window around it, or the folder's page. */
export function drawnRange(arrangement: Arrangement, n: number, selected: number): [number, number] {
  if (arrangement === "folder") {
    const page = Math.floor(Math.max(0, selected) / FOLDER_PLACES);
    return [page * FOLDER_PLACES, Math.min(n, (page + 1) * FOLDER_PLACES)];
  }
  const from = Math.max(0, Math.min(selected - DRAWN_SPAN, n - 2 * DRAWN_SPAN - 1));
  return [from, Math.min(n, from + 2 * DRAWN_SPAN + 1)];
}

