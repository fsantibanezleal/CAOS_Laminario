// A slide as it lies in a drawer's tray: glass drawn at its format's proportion and at the tray's scale (so a
// thin section is visibly shorter than a 76 x 26 mm slide), the label end first with the collection's hue band, the
// catalogue number and the name, and the specimen's thumbnail in the coverslip area. Below the glass, the
// preparation, the place and the date. The whole slide is one link to its place.
import type { CSSProperties } from "react";
import { Link } from "wouter";
import type { SlideSummary } from "../contract/catalog";
import { useI18n } from "../i18n";
import { collectionOf, localised, type TreeIndex } from "../tree/TreeProvider";
import { Icon } from "../ui/Icon";
import { Fragment } from "react";
import { breakPoints, geometry, nameParts } from "./names";
import styles from "./TraySlide.module.css";

export function TraySlide({ slide, tree }: { slide: SlideSummary; tree: TreeIndex }) {
  const { lang, date } = useI18n();
  const { long, short, label } = geometry(slide.format);
  const collection = collectionOf(slide.placement.node) ?? "life.plants";
  const hueName = collection.split(".")[1];
  const node = tree.byId.get(slide.placement.node);
  const preparation = tree.facets.get("preparation")?.values.find((v) => v.id === slide.preparation);
  const catalogue = slide.label?.catalogue_number || slide.id;
  const country = slide.label?.country ? tree.countries[slide.label.country]?.[lang] : undefined;
  const place = [slide.label?.locality_text, country].filter((p, i, all) => p && all.indexOf(p) === i).join(", ");
  const collected = slide.label?.collected_on;
  const style = { "--long": long, "--short": short, "--label": label, "--tag-hue": `var(--h-${hueName})` } as
    CSSProperties;

  const details = [preparation ? localised(preparation.name, lang) : slide.preparation, place,
    collected ? date(collected, { year: "numeric", month: "short", day: "numeric" }) : ""].filter(Boolean);

  return (
    <Link href={`/s/${slide.id}`} className={styles.slide} style={style} data-slide={slide.id}
      data-format={`${long}x${short}`}>
      <span className={styles.glass}>
        <span className={styles.label}>
          <span className={styles.band} aria-hidden="true" />
          <span className={styles.catalogue}>
            {breakPoints(catalogue).map((piece, i) => <Fragment key={i}>{i ? <wbr /> : null}{piece}</Fragment>)}
          </span>
          <span className={styles.name}>
            {nameParts(slide.anchor).map((part, i) => (
              <span key={i} className={part.italic ? styles.italic : undefined}>{i ? " " : ""}{part.text}</span>
            ))}
          </span>
          <Icon name={node?.icon ?? collection} size={16} className={styles.icon} />
        </span>
        <span className={styles.cover}>
          {slide.thumbnail_url ? (
            <img src={slide.thumbnail_url} alt="" loading="lazy" decoding="async" className={styles.thumb}
              onError={(e) => { e.currentTarget.hidden = true; }} />
          ) : null}
        </span>
      </span>
      <span className={styles.caption}>{details.join(" · ")}</span>
    </Link>
  );
}
