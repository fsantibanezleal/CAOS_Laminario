// The landing place (U17): the collection is shown as glass slides. The introduction and the search lie on a glass
// panel; each realm (Life, Earth, Matter) is a glass slide with its icon, name and description, and its collections
// are a set of glass slides in the arrangement the visitor chose (a carousel, a cabinet drawer, a slide box, a
// folder), each with the collection's icon under the coverslip, its name on the left end and its counts on the right.
import { useMemo, useState, type FormEvent } from "react";
import { Link, useLocation } from "wouter";
import { useRoom } from "../../design/theme";
import { GlassPanel } from "../../glass/GlassPanel";
import { GlassSet } from "../../glass/GlassSet";
import { nodeItem } from "../../glass/items";
import { useI18n } from "../../i18n";
import { Place } from "../../router/Place";
import { localised, useTree, type TreeIndex } from "../../tree/TreeProvider";
import { Button } from "../../ui/Button";
import { SearchField } from "../../ui/Field";
import { Glyph } from "../../ui/Icon";
import { TreeGate } from "../TreeGate";
import styles from "./RealmsPlace.module.css";

export function RealmsPlace() {
  const { t } = useI18n();
  const tree = useTree();
  return (
    <Place title={t("app.name")} heading={t("realms.title")} ready={tree.state !== "loading"}>
      <TreeGate tree={tree}>{(index) => <Realms tree={index} />}</TreeGate>
    </Place>
  );
}

function Realms({ tree }: { tree: TreeIndex }) {
  const i18n = useI18n();
  const { t, plural, lang } = i18n;
  const { room } = useRoom();
  const [, navigate] = useLocation();
  const [q, setQ] = useState("");
  const collections = tree.realms.flatMap((r) => r.children ?? []);
  const slides = tree.realms.reduce((n, r) => n + (r.slide_count ?? 0), 0);
  const sets = useMemo(() => tree.realms.map((realm) => ({
    realm, items: (realm.children ?? []).map((c) => nodeItem(c, i18n)) })),
  // The items follow the tree, the language and the room's colours.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [tree, lang, room]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    navigate(q.trim() ? `/search?${new URLSearchParams({ q: q.trim() })}` : "/search");
  };

  return (
    <>
      <GlassPanel title={t("app.name")} icon="life" className={styles.lead}>
        <p className={styles.intro}>{t("realms.intro")}</p>
        <form role="search" className={styles.search} onSubmit={submit}>
          <SearchField label={t("search.field")} hint={t("search.hint")} value={q} onChange={(e) => setQ(e.target.value)}
            onClear={() => setQ("")} />
          <Button type="submit" variant="primary" icon="search">{t("action.search")}</Button>
        </form>
        <p className={styles.totals}>
          <span>{t("realms.totals", { slides: plural("count.slides", slides),
            collections: plural("count.collections", collections.length) })}</span>
          <Link href="/map" className={styles.mapLink}><Glyph name="map" size={20} />{t("realms.map")}</Link>
        </p>
      </GlassPanel>

      {sets.map(({ realm, items }) => (
        <section key={realm.id} id={realm.id} className={styles.realm} aria-labelledby={`realm-${realm.id}`}>
          <GlassPanel as="header" icon={realm.id} title={<span id={`realm-${realm.id}`}>{localised(realm.name, lang)}</span>}
            className={styles.realmHead}>
            <p className={styles.realmAbout}>{localised(realm.about, lang)}</p>
            <p className={styles.realmCount}>{plural("count.slides", realm.slide_count ?? 0)}</p>
          </GlassPanel>
          <GlassSet items={items} name={realm.id} title={localised(realm.name, lang)}
            label={t("realms.set", { realm: localised(realm.name, lang) })} />
        </section>
      ))}
    </>
  );
}
