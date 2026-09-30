// A glass slide drawn flat in the page, the same object as in the scene: the frosted left end with the name, the
// sample under its coverslip (the icon or the specimen's image), the right end with the facts; or the photograph of
// the whole slide. Shown where the device draws no 3D, while the scene loads, and wherever a small slide is enough.
import type { CSSProperties } from "react";
import { Link } from "wouter";
import { Icon } from "../ui/Icon";
import type { GlassItem } from "./model";
import styles from "./FlatGlassSlide.module.css";

export function FlatGlassSlide({ item, current = false, compact = false }: { item: GlassItem; current?: boolean;
  compact?: boolean }) {
  const { long, short, label } = item.format;
  const style = { "--long": long, "--short": short, "--label": label, "--tag-hue": item.hue } as CSSProperties;
  return (
    <Link href={item.href} className={[styles.slide, compact ? styles.compact : "", item.empty ? styles.empty : ""]
      .join(" ")} style={style} aria-current={current ? "page" : undefined} data-glass-flat={item.id}
      data-slide={item.href.startsWith("/s/") ? item.id : undefined}
      data-format={`${item.format.long}x${item.format.short}`}>
      {item.photo ? (
        <img className={styles.photo} src={item.photo} alt="" loading="lazy" decoding="async" />
      ) : (
        <>
          <span className={styles.label}>
            <span className={styles.band} aria-hidden="true" />
            <span className={[styles.name, item.italic ? styles.italic : ""].join(" ")}>{item.name}</span>
            {item.reference && !compact ? <span className={styles.reference}>{item.reference}</span> : null}
          </span>
          <span className={styles.sample}>
            <span className={styles.cover}>
              {item.image ? <img src={item.image} alt="" loading="lazy" decoding="async" /> :
                item.icon ? <Icon name={item.icon} size={48} className={styles.icon} /> : null}
            </span>
          </span>
          <span className={styles.facts}>
            {item.facts.slice(0, compact ? 1 : 4).map((f) => <span key={f}>{f}</span>)}
          </span>
        </>
      )}
      {item.photo ? <span className={styles.srName}>{item.name}</span> : null}
    </Link>
  );
}
