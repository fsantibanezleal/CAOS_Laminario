// The landing place: the three realms (Life, Earth, Matter) with their collections as cabinets, a search field and
// the way to the map. Each cabinet front shows the collection's icon in its hue, its name, and how many slides and
// drawers it holds.
import { useState, type CSSProperties, type FormEvent } from "react";
import { Link, useLocation } from "wouter";
import type { CollectionNodeRecord } from "../../contract/catalog";
import { useI18n } from "../../i18n";
import { Place } from "../../router/Place";
import { localised, nodeHref, useTree, type TreeIndex } from "../../tree/TreeProvider";
import { Button } from "../../ui/Button";
import { SearchField } from "../../ui/Field";
import { Glyph, Icon } from "../../ui/Icon";
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
  const { t, plural, lang } = useI18n();
  const [, navigate] = useLocation();
  const [q, setQ] = useState("");
  const collections = tree.realms.flatMap((r) => r.children ?? []);
  const slides = tree.realms.reduce((n, r) => n + (r.slide_count ?? 0), 0);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    navigate(q.trim() ? `/search?${new URLSearchParams({ q: q.trim() })}` : "/search");
  };

  return (
    <>
      <div className={styles.lead}>
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
      </div>

      {tree.realms.map((realm) => (
        <section key={realm.id} id={realm.id} className={styles.realm} aria-labelledby={`realm-${realm.id}`}>
          <header className={styles.realmHead}>
            <Icon name={realm.id} size={48} className={styles.realmIcon} />
            <div>
              <h2 id={`realm-${realm.id}`} className={styles.realmName}>{localised(realm.name, lang)}</h2>
              <p className={styles.realmAbout}>{localised(realm.about, lang)}</p>
            </div>
            <p className={styles.realmCount}>{plural("count.slides", realm.slide_count ?? 0)}</p>
          </header>
          <ul className={styles.cabinets}>
            {(realm.children ?? []).map((c) => <li key={c.id}><Cabinet node={c} /></li>)}
          </ul>
        </section>
      ))}
    </>
  );
}

function Cabinet({ node }: { node: CollectionNodeRecord }) {
  const { plural, lang } = useI18n();
  const drawers = (node.children ?? []).length;
  const hue = { "--tag-hue": `var(--h-${node.id.split(".")[1]})` } as CSSProperties;
  return (
    <Link href={nodeHref(node.id)} className={styles.cabinet} style={hue}>
      <span className={styles.cornice} aria-hidden="true" />
      <Icon name={node.id} size={48} className={styles.cabinetIcon} />
      <span className={styles.cabinetName}>{localised(node.name, lang)}</span>
      <span className={styles.cabinetFacts}>
        <span>{plural("count.slides", node.slide_count ?? 0)}</span>
        <span>{plural("count.drawers", drawers)}</span>
      </span>
      <span className={styles.drawerLines} aria-hidden="true">
        {Array.from({ length: Math.min(drawers, 4) }, (_, i) => <span key={i} />)}
      </span>
    </Link>
  );
}
