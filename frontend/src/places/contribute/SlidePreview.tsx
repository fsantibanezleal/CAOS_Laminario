// The slide as it is being described, drawn to scale in millimetres: the glass of its format, the frosted end with
// the label (the name, the catalogue number, the date and a place for the QR code the label will carry), and the
// coverslip over the specimen. It changes as the fields do, so the object is in view while it is described; the
// published slide's own drawing, with its real label and code, is made by the server (app/labels).
import { COVERSLIP_MM, SLIDE_MM, type CaseDraft } from "../../contribute/draft";
import { useI18n } from "../../i18n";
import styles from "./Contribute.module.css";

function mm(value: string): number | null {
  const n = Number(value.trim().replace(",", "."));
  return Number.isFinite(n) && n > 0 ? n : null;
}

export function slideSize(draft: CaseDraft): [number, number] {
  const s = draft.slide;
  if (s.format !== "custom") return SLIDE_MM[s.format];
  const w = mm(s.customW) ?? 76;
  const h = mm(s.customH) ?? 26;
  return [Math.max(w, h), Math.min(w, h)];
}

export function coverSize(draft: CaseDraft): [number, number] | null {
  const s = draft.slide;
  if (s.coverslip === "none") return null;
  if (s.coverslip !== "custom") return COVERSLIP_MM[s.coverslip];
  const w = mm(s.coverW);
  const h = mm(s.coverH);
  return w && h ? [Math.max(w, h), Math.min(w, h)] : null;
}

export function SlidePreview({ draft }: { draft: CaseDraft }) {
  const { t } = useI18n();
  const [w, h] = slideSize(draft);
  const label = Math.min(24, w * 0.3);
  const cover = coverSize(draft);
  const free = w - label;
  const fits = cover ? cover[0] <= free && cover[1] <= h : true;
  const [cw, ch] = cover ? [Math.min(cover[0], free - 1), Math.min(cover[1], h - 1)] : [0, 0];
  const cx = label + (free - cw) / 2;
  const cy = (h - ch) / 2;
  const anchor = draft.specimen.anchor;
  const name = anchor?.name ?? t("preview.unnamed");
  const number = draft.slide.catalogueNumber.trim();
  const date = draft.specimen.collectedOn.trim();
  const pad = 1.4;
  const qr = Math.min(label - 2 * pad, h * 0.34);
  const described = [name, number, t(`format.${draft.slide.format}`),
    cover ? t("preview.coverslip", { w: cover[0], h: cover[1] }) : t("coverslip.none")].filter(Boolean).join(", ");

  return (
    <figure className={styles.preview}>
      <svg viewBox={`-1.5 -1.5 ${w + 3} ${h + 3}`} role="img" aria-label={described} className={styles.previewSvg}>
        <rect x={0} y={0} width={w} height={h} rx={0.8} className={styles.glass} />
        <rect x={0} y={0} width={label} height={h} rx={0.8} className={styles.frost} />
        <rect x={pad} y={pad} width={label - 2 * pad} height={h - 2 * pad} rx={0.3} className={styles.labelPaper} />
        <text x={pad + 0.9} y={pad + 3.2} className={styles.labelName}
          fontStyle={anchor?.kind === "taxon" ? "italic" : "normal"}>
          {name.length > 22 ? `${name.slice(0, 21)}…` : name}
        </text>
        {number ? <text x={pad + 0.9} y={pad + 6} className={styles.labelLine}>{number}</text> : null}
        {date ? <text x={pad + 0.9} y={pad + 8.6} className={styles.labelLine}>{date}</text> : null}
        <rect x={label - pad - qr - 0.6} y={h - pad - qr - 0.6} width={qr} height={qr} className={styles.qrPlace} />
        {cover ? (
          <>
            <ellipse cx={cx + cw / 2} cy={cy + ch / 2} rx={cw * 0.28} ry={ch * 0.3} className={styles.specimenMark} />
            <rect x={cx} y={cy} width={cw} height={ch} rx={0.2} className={styles.coverslip}
              data-fits={fits ? undefined : "no"} />
          </>
        ) : (
          <ellipse cx={label + free / 2} cy={h / 2} rx={free * 0.18} ry={h * 0.26} className={styles.specimenMark} />
        )}
      </svg>
      <figcaption className={styles.previewCaption}>
        <span>{t(`format.${draft.slide.format}`)}</span>
        <span>{t("preview.size", { w: Math.round(w * 10) / 10, h: Math.round(h * 10) / 10 })}</span>
        {cover && !fits ? <span className={styles.previewWarn}>{t("preview.coverTooLarge")}</span> : null}
      </figcaption>
    </figure>
  );
}
