// Colour arithmetic for the token build and the contrast gate: OKLCH to sRGB (CSS Color 4, Ottosson's OKLab) with
// gamut mapping by chroma reduction, and the WCAG 2.2 relative luminance and contrast ratio.

const toLinear = ([L, a, b]) => {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
};

const lab = (L, C, h) => [L, C * Math.cos((h * Math.PI) / 180), C * Math.sin((h * Math.PI) / 180)];
const inGamut = (rgb) => rgb.every((x) => x >= -1e-6 && x <= 1 + 1e-6);

/** The largest chroma at or below C that stays inside sRGB at the same lightness and hue. */
export function gamutChroma(L, C, h) {
  if (inGamut(toLinear(lab(L, C, h)))) return C;
  let lo = 0;
  let hi = C;
  for (let i = 0; i < 40; i += 1) {
    const mid = (lo + hi) / 2;
    if (inGamut(toLinear(lab(L, mid, h)))) lo = mid;
    else hi = mid;
  }
  return lo;
}

const encode = (x) => {
  const v = Math.min(Math.max(x, 0), 1);
  return v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055;
};

/** An OKLCH colour as the sRGB hex the browser will show (after gamut mapping). */
export function oklchToHex([L, C, h]) {
  const rgb = toLinear(lab(L, gamutChroma(L, C, h), h)).map(encode);
  return `#${rgb.map((v) => Math.round(v * 255).toString(16).padStart(2, "0")).join("")}`;
}

/** WCAG 2.2 relative luminance of an 8-bit sRGB hex colour. */
export function luminance(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG 2.2 contrast ratio, (L1 + 0.05) / (L2 + 0.05) with L1 the lighter. */
export function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

/** The sRGB hex of every colour token of a room, and of every collection hue at the room's lightness and chroma. */
export function resolveRoom(tokens, room) {
  const spec = tokens.rooms[room];
  const colours = Object.fromEntries(Object.entries(spec.colours).map(([k, v]) => [k, oklchToHex(v)]));
  const [L, C] = spec.hue;
  const hues = Object.fromEntries(Object.entries(tokens.collections).map(([k, h]) => [k, oklchToHex([L, C, h])]));
  return { colours, hues };
}
