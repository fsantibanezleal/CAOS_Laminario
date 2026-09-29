// The masthead every place shares: the wordmark (home), the ways into the collection (the cabinets, search, the
// map), the room and the language, and the trail of places below. The current way in is marked for assistive
// technology (aria-current) and drawn in brass.
import type { ReactNode } from "react";
import { Link, useLocation } from "wouter";
import { useI18n } from "../i18n";
import { Glyph } from "./Icon";
import styles from "./Masthead.module.css";
import { LanguageSwitch, RoomSwitch } from "./Switches";

const WAYS = [
  { href: "/", glyph: "cabinet", key: "nav.collections", matches: (p: string) => p === "/" || p.startsWith("/c/") },
  { href: "/search", glyph: "search", key: "nav.search", matches: (p: string) => p.startsWith("/search") },
  { href: "/map", glyph: "map", key: "nav.map", matches: (p: string) => p.startsWith("/map") },
] as const;

export function Masthead({ trail }: { trail?: ReactNode }) {
  const { t } = useI18n();
  const [location] = useLocation();
  return (
    <header className={styles.masthead}>
      <a className="skip-link" href="#content">{t("app.skip")}</a>
      <div className={styles.row}>
        <Link href="/" className={styles.wordmark}>
          <Glyph name="slide" size={32} />
          <span className={styles.name}>{t("app.name")}</span>
          <span className={styles.tagline}>{t("app.tagline")}</span>
        </Link>
        <nav aria-label={t("nav.label")} className={styles.ways}>
          {WAYS.map((way) => {
            const current = way.matches(location);
            return (
              <Link key={way.href} href={way.href} className={styles.way} aria-current={current ? "page" : undefined}>
                <Glyph name={way.glyph} size={20} />
                <span>{t(way.key)}</span>
              </Link>
            );
          })}
        </nav>
        <div className={styles.switches}>
          <RoomSwitch />
          <LanguageSwitch />
        </div>
      </div>
      {trail ? <div className={styles.trail}>{trail}</div> : null}
    </header>
  );
}
