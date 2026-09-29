// "Cite this slide" on the slide place (U15, R-1503): the slide's citation and each image's attribution, each with a
// button that copies it; the About place says how they are built.
import { Link } from "wouter";
import type { SlideRecord } from "../contract/catalog";
import { useI18n } from "../i18n";
import type { MessageKey } from "../i18n/en";
import { localised, type TreeIndex } from "../tree/TreeProvider";
import { Button } from "../ui/Button";
import { useToast } from "../ui/Overlay";
import { attribution, slideCitation, type CiteWords } from "./cite";
import styles from "./Cite.module.css";

export function CiteSlide({ record, tree }: { record: SlideRecord; tree: TreeIndex }) {
  const { t, lang, date } = useI18n();
  const toast = useToast();
  const words: CiteWords = { kind: t("cite.kind"), readOn: t("cite.readOn"), by: t("cite.by"), from: t("cite.from"),
    unknownAuthor: t("cite.unknown"), pyramid: t("cite.pyramid"), fused: t("cite.fused"),
    reencoded: t("cite.reencoded") };
  const prep = tree.facets.get("preparation")?.values.find((v) => v.id === record.label.preparation);
  const preparation = prep ? localised(prep.name, lang).toLowerCase() : record.label.preparation;
  const today = date(new Date().toISOString().slice(0, 10), { year: "numeric", month: "long", day: "numeric" });
  const lines = [
    { key: "slide", label: t("cite.slide"), text: slideCitation(record, preparation, today, words) },
    ...record.assets.map((a) => ({ key: String(a.id), label: t(`role.${a.role}` as MessageKey),
      text: attribution(a, record, t(`role.${a.role}` as MessageKey), words) })),
  ];
  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.show(t("cite.copied"), "good");
    } catch {
      toast.show(t("cite.copyFailed"), "warn");
    }
  };
  return (
    <section aria-labelledby="cite" className={styles.cite}>
      <h2 id="cite" className={styles.title}>{t("cite.title")}</h2>
      <ul className={styles.lines}>
        {lines.map((line) => (
          <li key={line.key} data-cite={line.key}>
            <span className={styles.label}>{line.label}</span>
            <p className={styles.text}>{line.text}</p>
            <Button size="small" onClick={() => void copy(line.text)}
              aria-label={`${t("cite.copy")}: ${line.label}`}>{t("cite.copy")}</Button>
          </li>
        ))}
      </ul>
      <p className={styles.more}><Link href="/about#cite">{t("cite.more")}</Link></p>
    </section>
  );
}
