// The foot of every place (U15): the way to About the collection, its licences and how to cite, one click from
// anywhere (R-084), and the map data's credit.
import { Link } from "wouter";
import { useI18n } from "../i18n";
import styles from "./Footer.module.css";

export function Footer() {
  const { t } = useI18n();
  return (
    <footer className={styles.footer}>
      <nav aria-label={t("footer.label")}>
        <ul className={styles.links}>
          <li><Link href="/about">{t("footer.about")}</Link></li>
          <li><Link href="/about#licences">{t("footer.licences")}</Link></li>
          <li><Link href="/about#cite">{t("footer.cite")}</Link></li>
        </ul>
      </nav>
      <p className={styles.note}>{t("footer.note")}</p>
    </footer>
  );
}
