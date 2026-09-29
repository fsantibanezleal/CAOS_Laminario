// The About place's figures (U15, R-1504): drawn inline, so their colours are the room's tokens (an SVG loaded as an
// image cannot read the page's colours). Each takes its labels in the page's language.
import type { ReactNode } from "react";
import type { FigureId } from "./model";
import styles from "./About.module.css";

type Labels = Record<string, string>;

function Frame({ title, children, height = 250 }: { title: string; children: ReactNode; height?: number }) {
  return (
    <svg viewBox={`0 0 640 ${height}`} role="img" aria-label={title} className={styles.figureSvg}>
      <rect x="0" y="0" width="640" height={height} rx="6" fill="var(--c-sunken)" />
      {children}
    </svg>
  );
}

const text = { fill: "var(--c-ink)", fontSize: 13, fontFamily: "var(--f-reading)" } as const;
const muted = { fill: "var(--c-ink-muted)", fontSize: 12, fontFamily: "var(--f-reading)" } as const;

function Pyramid({ l }: { l: Labels }) {
  // Level 0 is 4 x 3 tiles; each level below halves both sides.
  const levels = [{ w: 256, h: 176, cols: 4, rows: 3 }, { w: 128, h: 88, cols: 2, rows: 2 },
    { w: 64, h: 44, cols: 1, rows: 1 }, { w: 32, h: 22, cols: 1, rows: 1 }];
  let x = 24;
  return (
    <Frame title={l.title} height={264}>
      {levels.map((lv, i) => {
        const left = x;
        x += lv.w + 36;
        const top = 30;
        const tw = lv.w / lv.cols;
        const th = lv.h / lv.rows;
        return (
          <g key={i}>
            <rect x={left} y={top} width={lv.w} height={lv.h} fill="var(--c-surface)" stroke="var(--c-edge)" />
            {Array.from({ length: lv.cols - 1 }, (_, c) => (
              <line key={`c${c}`} x1={left + (c + 1) * tw} y1={top} x2={left + (c + 1) * tw} y2={top + lv.h}
                stroke="var(--c-rule)" />
            ))}
            {Array.from({ length: lv.rows - 1 }, (_, r) => (
              <line key={`r${r}`} x1={left} y1={top + (r + 1) * th} x2={left + lv.w} y2={top + (r + 1) * th}
                stroke="var(--c-rule)" />
            ))}
            {i === 0 ? <rect x={left + tw} y={top + th} width={tw} height={th} fill="var(--c-accent)" opacity="0.28"
              stroke="var(--c-accent)" strokeWidth="2" /> : null}
            <text x={left} y={top + lv.h + 22} {...text}>{`${l.level} ${i}`}</text>
            {i === 0 ? <text x={left} y={top + lv.h + 40} {...muted}>{l.full}</text> : null}
          </g>
        );
      })}
      <text x={24 + 256 / 4 + 4} y={30 + 176 / 3 + 20} {...muted}>{l.tile}</text>
      <text x={316} y={172} {...muted}>{l.half}</text>
    </Frame>
  );
}

function Objectives({ l }: { l: Labels }) {
  // One 0.5 um image pixel drawn at z = p M / 10 screen pixels: 10x gives 0.5, 20x gives 1, 40x gives 2 (digital).
  const panels = [{ m: 10, z: 0.5 }, { m: 20, z: 1 }, { m: 40, z: 2 }];
  const unit = 14; // screen pixels drawn per unit of z
  return (
    <Frame title={l.title}>
      {panels.map((p, i) => {
        const left = 24 + i * 204;
        const cell = unit * p.z;
        const n = Math.floor(168 / cell);
        return (
          <g key={p.m}>
            <rect x={left} y={24} width={168} height={168} fill="var(--c-surface)" stroke="var(--c-edge)" />
            {Array.from({ length: n * n }, (_, k) => {
              const r = Math.floor(k / n);
              const c = k % n;
              return (r + c) % 2 ? <rect key={k} x={left + c * cell} y={24 + r * cell} width={cell} height={cell}
                fill="var(--h-rocks)" opacity="0.35" /> : null;
            })}
            <text x={left} y={212} {...text}>{`${p.m}x   z = ${p.z}`}</text>
            <text x={left} y={230} {...muted}>{p.z > 1 ? l.digital : l.screen}</text>
          </g>
        );
      })}
    </Frame>
  );
}

function Stack({ l }: { l: Labels }) {
  const plane = (y: number, sharp: number, key: number) => (
    <g key={key}>
      <path d={`M40 ${y} L220 ${y} L260 ${y + 34} L80 ${y + 34} Z`} fill="var(--c-surface)" stroke="var(--c-edge)" />
      <ellipse cx={100 + sharp * 50} cy={y + 17} rx="22" ry="9" fill="var(--c-accent)" opacity="0.55" />
    </g>
  );
  return (
    <Frame title={l.title}>
      {[0, 1, 2].map((k) => plane(40 + k * 52, k, k))}
      <text x={40} y={218} {...text}>{l.planes}</text>
      <line x1="280" y1="110" x2="326" y2="110" stroke="var(--c-ink-muted)" strokeWidth="2" />
      <path d="M326 103 L338 110 L326 117 Z" fill="var(--c-ink-muted)" />
      <rect x="350" y="52" width="120" height="120" fill="var(--c-surface)" stroke="var(--c-edge)" />
      {[0, 1, 2].map((k) => <ellipse key={k} cx={380 + k * 30} cy={80 + k * 30} rx="18" ry="9" fill="var(--c-accent)"
        opacity="0.55" />)}
      <text x={350} y={196} {...text}>{l.composite}</text>
      <rect x="494" y="52" width="120" height="120" fill="var(--c-surface)" stroke="var(--c-edge)" />
      {[0, 1, 2].map((k) => <rect key={k} x={494} y={52 + k * 40} width={120} height={40} fill="var(--c-ink)"
        opacity={0.15 + k * 0.25} />)}
      <text x={494} y={196} {...text}>{l.height}</text>
    </Frame>
  );
}

function Polarised({ l }: { l: Labels }) {
  const column = (left: number, crossed: boolean, label: string) => (
    <g>
      <text x={left} y={28} {...text}>{label}</text>
      {crossed ? (
        <g>
          <rect x={left} y={44} width={200} height={28} fill="var(--c-surface)" stroke="var(--c-edge)" />
          {Array.from({ length: 9 }, (_, k) => <line key={k} x1={left + 20 * (k + 1)} y1={46} x2={left + 20 * (k + 1)}
            y2={70} stroke="var(--c-ink-muted)" />)}
          <text x={left + 212} y={63} {...muted}>{l.analyser}</text>
        </g>
      ) : null}
      <rect x={left} y={96} width={200} height={20} fill="var(--h-rocks)" opacity="0.5" />
      <text x={left + 212} y={111} {...muted}>{l.section}</text>
      <rect x={left} y={140} width={200} height={28} fill="var(--c-surface)" stroke="var(--c-edge)" />
      {Array.from({ length: 4 }, (_, k) => <line key={k} x1={left + 4} y1={145 + 6 * k} x2={left + 196} y2={145 + 6 * k}
        stroke="var(--c-ink-muted)" />)}
      <text x={left + 212} y={159} {...muted}>{l.polariser}</text>
      <line x1={left + 100} y1={228} x2={left + 100} y2={176} stroke="var(--c-warn)" strokeWidth="3" />
      <text x={left + 108} y={222} {...muted}>{l.light}</text>
    </g>
  );
  return (
    <Frame title={l.title}>
      {column(24, false, l.ppl)}
      {column(330, true, l.xpl)}
    </Frame>
  );
}

function Geoprivacy({ l }: { l: Labels }) {
  const box = (left: number) => <rect x={left} y={24} width={176} height={150} fill="var(--c-surface)"
    stroke="var(--c-edge)" />;
  return (
    <Frame title={l.title}>
      {box(24)}
      <circle cx={24 + 96} cy={24 + 70} r="6" fill="var(--c-accent)" />
      <text x={24} y={198} {...text}>{l.open}</text>
      {box(232)}
      <rect x={232 + 38} y={24 + 30} width={100} height={90} fill="var(--c-accent)" opacity="0.18"
        stroke="var(--c-accent)" strokeDasharray="5 4" />
      <circle cx={232 + 70} cy={24 + 92} r="5" fill="var(--c-accent)" />
      <text x={232} y={198} {...text}>{l.obscured.split(":")[0]}:</text>
      <text x={232} y={216} {...muted}>{l.obscured.split(":").slice(1).join(":").trim()}</text>
      {box(440)}
      <circle cx={440 + 88} cy={24 + 75} r="14" fill="none" stroke="var(--c-ink-muted)" strokeDasharray="4 3" />
      <line x1={440 + 78} y1={24 + 85} x2={440 + 98} y2={24 + 65} stroke="var(--c-ink-muted)" strokeWidth="1.5" />
      <text x={440} y={198} {...text}>{l.private}</text>
    </Frame>
  );
}

export function Figure({ id, labels }: { id: FigureId; labels: Labels }) {
  switch (id) {
    case "pyramid": return <Pyramid l={labels} />;
    case "objectives": return <Objectives l={labels} />;
    case "stack": return <Stack l={labels} />;
    case "polarised": return <Polarised l={labels} />;
    case "geoprivacy": return <Geoprivacy l={labels} />;
  }
}
