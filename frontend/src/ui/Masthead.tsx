// The masthead every place shares: the wordmark (home), the trail of places, the room and the language.
import type { ReactNode } from "react";
import { useI18n } from "../i18n";
import { Glyph } from "./Icon";
import styles from "./Masthead.module.css";
import { LanguageSwitch, RoomSwitch } from "./Switches";

export function Masthead({ trail }: { trail?: ReactNode }) {
  const { t } = useI18n();
  return (
    <header className={styles.masthead}>
      <a className="skip-link" href="#content">{t("app.skip")}</a>
      <div className={styles.row}>
        <a href="/" className={styles.wordmark}>
          <Glyph name="slide" size={32} />
          <span className={styles.name}>{t("app.name")}</span>
          <span className={styles.tagline}>{t("app.tagline")}</span>
        </a>
        <div className={styles.switches}>
          <RoomSwitch />
          <LanguageSwitch />
        </div>
      </div>
      {trail ? <div className={styles.trail}>{trail}</div> : null}
    </header>
  );
}
