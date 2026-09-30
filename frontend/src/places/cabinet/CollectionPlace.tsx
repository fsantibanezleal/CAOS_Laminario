// /c/<collection>[/<drawer>[/<group>]] (U17): a collection shows its drawers, and a drawer (a sub-collection or a
// group) its slides, all as glass slides in the arrangement the visitor chose. What goes in a node (its description and
// its rule, each taxon linked to its GBIF page) lies on a glass panel; a drawer's neighbouring groups are glass slides
// too, the current one chosen.
import { useMemo, useState, type CSSProperties } from "react";
import { Link, useParams } from "wouter";
import type { CollectionNodeRecord } from "../../contract/catalog";
import { useRoom } from "../../design/theme";
import { Explorer } from "../../explore/Explorer";
import { GlassPanel } from "../../glass/GlassPanel";
import { GlassSet } from "../../glass/GlassSet";
import { hueToken, nodeItem } from "../../glass/items";
import type { GlassItem } from "../../glass/model";
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
  const hue = { "--tag-hue": `var(${hueToken(node.id)})` } as CSSProperties;
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

/** The items of a set of nodes, remade when the language or the room changes. */
function useNodeItems(nodes: CollectionNodeRecord[],
  extra?: (items: GlassItem[], i18n: ReturnType<typeof useI18n>) => GlassItem[]): GlassItem[] {
  const i18n = useI18n();
  const { room } = useRoom();
  return useMemo(() => {
    const items = nodes.map((n) => nodeItem(n, i18n));
    return extra ? extra(items, i18n) : items;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, i18n.lang, room]);
}

function CabinetPlace({ tree, node }: { tree: TreeIndex; node: CollectionNodeRecord }) {
  const { t, plural, lang } = useI18n();
  const drawers = node.children ?? [];
  const items = useNodeItems(drawers);
  const name = localised(node.name, lang);
  return (
    <Place title={name} heading={<Heading node={node} />} trail={trailOf(tree, node, lang, t("nav.collections"))}>
      <GlassPanel title={name} icon={node.icon || node.id} hue={hueToken(node.id)} className={styles.lead}>
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
      </GlassPanel>
      <h2 className={styles.sectionTitle}>{t("cabinet.drawers")}</h2>
      <GlassSet items={items} name="drawers" title={name} hue={hueToken(node.id)}
        label={t("cabinet.set", { name })} />
    </Place>
  );
}

function DrawerPlace({ tree, node }: { tree: TreeIndex; node: CollectionNodeRecord }) {
  const { t, plural, lang } = useI18n();
  const [ready, setReady] = useState(false);
  const parent = tree.parentOf.get(node.id);
  const parentNode = parent ? tree.byId.get(parent) : undefined;
  const dividers = node.level === "group" && parentNode ? parentNode.children ?? [] : node.children ?? [];
  const whole = node.level === "group" && parentNode ? parentNode : undefined;
  const items = useNodeItems(dividers, (list, i18n) => whole ? [{ ...nodeItem(whole, i18n),
    name: i18n.t("drawer.whole", { name: localised(whole.name, i18n.lang) }) }, ...list] : list);
  const current = items.findIndex((i) => i.id === node.id);
  const name = localised(node.name, lang);
  return (
    <Place title={name} heading={<Heading node={node} />} ready={ready}
      trail={trailOf(tree, node, lang, t("nav.collections"))}>
      <GlassPanel title={name} icon={node.icon || node.id} hue={hueToken(node.id)} className={styles.lead}>
        <Rule node={node} summary={t("drawer.rules")} />
        <p className={styles.facts}><span>{plural("count.slides", node.slide_count ?? 0)}</span></p>
        {node.view ? <p className={styles.view}><Glyph name="info" size={20} />{t("drawer.view")}</p> : null}
      </GlassPanel>
      {items.length ? (
        <nav aria-label={t("drawer.dividers")} className={styles.dividers}>
          <h2 className={styles.sectionTitle}>{t("drawer.dividers")}</h2>
          <GlassSet items={items} name="dividers" title={name} hue={hueToken(node.id)} initial={Math.max(0, current)}
            label={t("drawer.dividers")} />
        </nav>
      ) : null}
      <h2 className={styles.sectionTitle}>{t("drawer.slides")}</h2>
      <Explorer tree={tree} node={node.id} only={node.view ? ["kind"] : undefined} onReady={setReady}
        setTitle={name} emptyTitle={t("drawer.empty.title")} emptyBody={t("drawer.empty.body")} />
    </Place>
  );
}
