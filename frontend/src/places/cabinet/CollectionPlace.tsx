// /c/<collection>[/<drawer>[/<group>]]: a cabinet (a collection) shows its drawers; a drawer (a sub-collection or a
// group) shows its slides on a tray, with its filters. Both say what goes in them: the node's rule, with each taxon
// linked to its GBIF page.
import { useState, type CSSProperties } from "react";
import { Link, useParams } from "wouter";
import type { CollectionNodeRecord } from "../../contract/catalog";
import { Explorer } from "../../explore/Explorer";
import { useI18n } from "../../i18n";
import { Place } from "../../router/Place";
import { localised, nodeFromPath, nodeHref, pathTo, useTree, type TreeIndex } from "../../tree/TreeProvider";
import type { Place as TrailPlace } from "../../ui/PlaceTrail";
import { Glyph, Icon } from "../../ui/Icon";
import { NotFoundPlace } from "../NotFoundPlace";
import { TreeGate } from "../TreeGate";
import styles from "./CollectionPlace.module.css";

export function CollectionPlace() {
  const params = useParams<{ "*": string }>();
  const tree = useTree();
  const { t } = useI18n();
  const segments = (params["*"] ?? "").split("/").filter(Boolean);
  if (tree.state !== "ready") {
    return <Place title={t("state.loading")}><TreeGate tree={tree}>{() => null}</TreeGate></Place>;
  }
  const node = nodeFromPath(tree.tree, segments);
  if (!node) return <NotFoundPlace />;
  return node.level === "collection"
    ? <CabinetPlace tree={tree.tree} node={node} />
    : <DrawerPlace key={node.id} tree={tree.tree} node={node} />;
}

function trailOf(tree: TreeIndex, node: CollectionNodeRecord, lang: "en" | "es", home: string): TrailPlace[] {
  return [{ label: home, href: "/" }, ...pathTo(tree, node.id).map((n) => ({
    label: localised(n.name, lang), href: nodeHref(n.id), icon: n.id }))];
}

function Heading({ node }: { node: CollectionNodeRecord }) {
  const { lang } = useI18n();
  const hue = { "--tag-hue": `var(--h-${node.id.split(".")[1]})` } as CSSProperties;
  return (
    <span className={styles.heading} style={hue}>
      <Icon name={node.icon || node.id} size={48} className={styles.headingIcon} />
      <span>{localised(node.name, lang)}</span>
    </span>
  );
}

/** What goes in a node: its description and its rule, each taxon linked to its page. */
function Rule({ node, summary }: { node: CollectionNodeRecord; summary: string }) {
  const { lang } = useI18n();
  const about = localised(node.about, lang);
  const rules = node.defined_by ?? [];
  return (
    <div className={styles.rule}>
      {about ? <p className={styles.about}>{about}</p> : null}
      {rules.length ? (
        <details className={styles.details}>
          <summary>{summary}</summary>
          <ul>
            {rules.map((r) => (
              <li key={`${r.kind}-${r.value}`}>
                {r.url ? <a href={r.url} target="_blank" rel="noreferrer">{r.label}</a> : r.label}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}

function CabinetPlace({ tree, node }: { tree: TreeIndex; node: CollectionNodeRecord }) {
  const { t, plural, lang } = useI18n();
  const drawers = node.children ?? [];
  return (
    <Place title={localised(node.name, lang)} heading={<Heading node={node} />}
      trail={trailOf(tree, node, lang, t("nav.collections"))}>
      <div className={styles.lead}>
        <Rule node={node} summary={t("cabinet.rules")} />
        <p className={styles.facts}>
          <span>{plural("count.slides", node.slide_count ?? 0)}</span>
          <span>{plural("count.drawers", drawers.length)}</span>
        </p>
        <p className={styles.ways}>
          <Link href={`/search?${new URLSearchParams({ node: node.id })}`}>
            <Glyph name="search" size={20} />{t("cabinet.all")}
          </Link>
          <Link href={`/map?${new URLSearchParams({ node: node.id })}`}>
            <Glyph name="map" size={20} />{t("cabinet.map")}
          </Link>
        </p>
      </div>
      <h2 className={styles.sectionTitle}>{t("cabinet.drawers")}</h2>
      <ul className={styles.drawers}>
        {drawers.map((d) => <li key={d.id}><DrawerFront node={d} /></li>)}
      </ul>
    </Place>
  );
}

/** A drawer front: oak, a brass label holder with the drawer's name and count, and a pull. */
function DrawerFront({ node }: { node: CollectionNodeRecord }) {
  const { t, plural, lang } = useI18n();
  const count = node.slide_count ?? 0;
  return (
    <Link href={nodeHref(node.id)} className={[styles.front, count ? "" : styles.emptyFront].join(" ")}>
      <Icon name={node.icon || node.id} size={32} className={styles.frontIcon} />
      <span className={styles.holder}>
        <span className={styles.frontName}>{localised(node.name, lang)}</span>
        <span className={styles.frontCount}>{count ? plural("count.slides", count) : t("cabinet.empty")}</span>
      </span>
      <span className={styles.pull} aria-hidden="true" />
    </Link>
  );
}

function DrawerPlace({ tree, node }: { tree: TreeIndex; node: CollectionNodeRecord }) {
  const { t, plural, lang } = useI18n();
  const [ready, setReady] = useState(false);
  const parent = tree.parentOf.get(node.id);
  const parentNode = parent ? tree.byId.get(parent) : undefined;
  const dividers = node.level === "group" && parentNode ? parentNode.children ?? [] : node.children ?? [];
  return (
    <Place title={localised(node.name, lang)} heading={<Heading node={node} />} ready={ready}
      trail={trailOf(tree, node, lang, t("nav.collections"))}>
      <div className={styles.lead}>
        <Rule node={node} summary={t("drawer.rules")} />
        {node.view ? <p className={styles.view}><Glyph name="info" size={20} />{t("drawer.view")}</p> : null}
      </div>
      {dividers.length ? (
        <nav aria-label={t("drawer.dividers")} className={styles.dividers}>
          <h2 className={styles.dividersTitle}>{t("drawer.dividers")}</h2>
          <ul>
            {node.level === "group" && parentNode ? (
              <li>
                <Link href={nodeHref(parentNode.id)} className={styles.divider}>
                  {t("drawer.whole", { name: localised(parentNode.name, lang) })}
                  <span className={styles.dividerCount}>{plural("count.slides", parentNode.slide_count ?? 0)}</span>
                </Link>
              </li>
            ) : null}
            {dividers.map((d) => (
              <li key={d.id}>
                <Link href={nodeHref(d.id)} className={styles.divider} aria-current={d.id === node.id ? "page" : undefined}>
                  <Icon name={d.icon || d.id} size={20} />
                  {localised(d.name, lang)}
                  <span className={styles.dividerCount}>{plural("count.slides", d.slide_count ?? 0)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
      <Explorer tree={tree} node={node.id} only={node.view ? ["kind"] : undefined} onReady={setReady}
        emptyTitle={t("drawer.empty.title")} emptyBody={t("drawer.empty.body")} />
    </Place>
  );
}
