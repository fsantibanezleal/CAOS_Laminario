// The trail of places a visitor stands in (realm > cabinet > drawer > slide > stage): a breadcrumb whose last place is
// the current one. Each earlier place is a link back to it.
import { Link } from "wouter";
import { useI18n } from "../i18n";
import styles from "./PlaceTrail.module.css";
import { Glyph, Icon } from "./Icon";

export interface Place {
  label: string;
  href?: string;
  icon?: string;
}

export function PlaceTrail({ places }: { places: Place[] }) {
  const { t } = useI18n();
  return (
    <nav aria-label={t("place.trail")} className={styles.trail}>
      <ol>
        {places.map((place, i) => {
          const last = i === places.length - 1;
          return (
            <li key={`${place.label}-${i}`}>
              {i > 0 ? <Glyph name="chevron-right" size={16} className={styles.sep} /> : null}
              {last || !place.href ? (
                <span aria-current={last ? "page" : undefined} className={last ? styles.current : undefined}>
                  {place.icon ? <Icon name={place.icon} size={16} /> : null}
                  {place.label}
                </span>
              ) : (
                <Link href={place.href}>
                  {place.icon ? <Icon name={place.icon} size={16} /> : null}
                  {place.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
