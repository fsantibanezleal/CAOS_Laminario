// Text on glass (U17): every panel of the interface (a drawer's description, the filters, About's sections, a form) is
// a glass slide drawn in the page. Its frosted end carries the collection's band, the icon and the title, as a slide's
// label names it; the content lies on the clear glass beside it. On a narrow screen the end is at the top.
import type { CSSProperties, ReactNode } from "react";
import { Icon } from "../ui/Icon";
import styles from "./GlassPanel.module.css";

export interface GlassPanelProps {
  children: ReactNode;
  title?: ReactNode;
  /** The heading level of the title (2 by default); the panel is a section named by it. */
  level?: 2 | 3;
  icon?: string;
  /** The hue token of the band ("--h-plants"); the accent by default. */
  hue?: string;
  as?: "section" | "header" | "div" | "aside" | "article" | "footer";
  className?: string;
  id?: string;
  /** A panel read as one piece of text (an empty state, a note): the end is narrower. */
  quiet?: boolean;
  /** The end above the glass, for a narrow column (the filters' rail). */
  stacked?: boolean;
}

export function GlassPanel({ children, title, level = 2, icon, hue = "--c-accent", as, className, id,
  quiet = false, stacked = false }: GlassPanelProps) {
  const Tag = as ?? "section";
  const headingId = id ? `${id}-title` : undefined;
  const heading = !title ? null : level === 3
    ? <h3 id={headingId} className={styles.title}>{title}</h3>
    : <h2 id={headingId} className={styles.title}>{title}</h2>;
  return (
    <Tag id={id} className={[styles.panel, quiet ? styles.quiet : "", stacked ? styles.stacked : "", className ?? ""]
      .join(" ")}
      style={{ "--tag-hue": `var(${hue})` } as CSSProperties}
      aria-labelledby={title && headingId ? headingId : undefined} data-glass-panel="">
      <div className={styles.end}>
        <span className={styles.band} aria-hidden="true" />
        {icon ? <Icon name={icon} size={32} className={styles.icon} /> : null}
        {heading}
      </div>
      <div className={styles.glass}>{children}</div>
    </Tag>
  );
}
