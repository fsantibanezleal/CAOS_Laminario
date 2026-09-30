// /identify: the slides waiting for identification (R-1307), oldest first so none waits forever, laid out as a tray
// like a drawer's; filtered by collection, kind and badge (the reference slides on request), and, for an identifier,
// without the slides they have identified. The filters live in the address, so a queue can be shared.
import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearch } from "wouter";
import { useSession } from "../../account/session";
import { communityApi, type QueueFilters } from "../../community/api";
import type { SlideSummary } from "../../contract/catalog";
import { useI18n } from "../../i18n";
import { Place } from "../../router/Place";
import { useRoom } from "../../design/theme";
import { GlassSet } from "../../glass/GlassSet";
import { slideItem } from "../../glass/items";
import { localised, useTree } from "../../tree/TreeProvider";
import { Button } from "../../ui/Button";
import { Checkbox } from "../../ui/Choice";
import { EmptyState, Skeleton } from "../../ui/Feedback";
import { Select } from "../../ui/Field";
import styles from "./Identify.module.css";

const PAGE = 24;

function readFilters(search: string): QueueFilters {
  const q = new URLSearchParams(search);
  const badge = q.get("badge");
  return {
    node: q.get("node") ?? "",
    kind: (q.get("kind") ?? "") as QueueFilters["kind"],
    badge: badge === "reference" || badge === "any" ? badge : "needs_id",
    unidentifiedByMe: q.get("mine") === "no",
  };
}

function writeFilters(f: QueueFilters): string {
  const q = new URLSearchParams();
  if (f.node) q.set("node", f.node);
  if (f.kind) q.set("kind", f.kind);
  if (f.badge && f.badge !== "needs_id") q.set("badge", f.badge);
  if (f.unidentifiedByMe) q.set("mine", "no");
  const s = q.toString();
  return s ? `/identify?${s}` : "/identify";
}

export function IdentifyPlace() {
  const { t, lang, plural } = useI18n();
  const tree = useTree();
  const session = useSession();
  const search = useSearch();
  const [, navigate] = useLocation();
  const filters = useMemo(() => readFilters(search), [search]);
  const [items, setItems] = useState<SlideSummary[] | null>(null);
  const [total, setTotal] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const [failed, setFailed] = useState(false);
  const key = JSON.stringify(filters);
  const i18n = useI18n();
  const { room } = useRoom();
  const glass = useMemo(() => (items && tree.state === "ready" ? items.map((s) => slideItem(s, tree.tree, i18n)) : []),
    // The items follow the queue, the language and the room's colours.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [items, tree, lang, room]);

  useEffect(() => {
    const controller = new AbortController();
    setItems(null);
    setFailed(false);
    communityApi.queue({ ...filters, limit: PAGE }, controller.signal).then((page) => {
      setItems(page.items);
      setTotal(page.total);
    }, () => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
    // The filters' text names the query.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, session.account]);

  const more = async () => {
    if (!items) return;
    setLoadingMore(true);
    try {
      const page = await communityApi.queue({ ...filters, offset: items.length, limit: PAGE });
      setItems([...items, ...page.items]);
      setTotal(page.total);
    } finally {
      setLoadingMore(false);
    }
  };

  const set = (change: Partial<QueueFilters>) => navigate(writeFilters({ ...filters, ...change }), { replace: true });

  const collections = tree.state === "ready" ? tree.tree.realms.flatMap((realm) => [
    { value: realm.id, label: localised(realm.name, lang) },
    ...(realm.children ?? []).map((c) => ({ value: c.id, label: `  ${localised(c.name, lang)}` })),
  ]) : [];

  return (
    <Place title={t("identify.title")} ready={items !== null} wide>
      <p className={styles.lead}>{t("identify.lead")}</p>
      <div className={styles.filters} role="search" aria-label={t("identify.filters")}>
        <Select label={t("identify.collection")} value={filters.node ?? ""}
          onChange={(e) => set({ node: e.target.value })}
          options={[{ value: "", label: t("identify.collection.all") }, ...collections]} />
        <Select label={t("identify.kind")} value={filters.kind ?? ""}
          onChange={(e) => set({ kind: e.target.value as QueueFilters["kind"] })}
          options={[{ value: "", label: t("identify.kind.all") },
            ...(["taxon", "rock", "mineral", "crystal", "material"] as const).map((k) => ({ value: k,
              label: t(`anchor.kind.${k}`) }))]} />
        <Select label={t("identify.badge")} value={filters.badge ?? "needs_id"}
          onChange={(e) => set({ badge: e.target.value as QueueFilters["badge"] })}
          options={[{ value: "needs_id", label: t("identify.badge.needs_id") },
            { value: "reference", label: t("identify.badge.reference") },
            { value: "any", label: t("identify.badge.any") }]} />
        {session.account ? (
          <Checkbox label={t("identify.notMine")} checked={Boolean(filters.unidentifiedByMe)}
            onChange={(e) => set({ unidentifiedByMe: e.target.checked })} />
        ) : null}
      </div>
      {!session.can("identify") ? (
        <p className={styles.note}>{session.account ? t("community.identifiersOnly") : t("community.signInToIdentify")}</p>
      ) : null}
      {failed ? <p role="alert" className={styles.problem}>{t("identify.failed")}</p> : null}
      {items === null && !failed ? <Skeleton lines={6} /> : null}
      {items !== null ? (
        <p className={styles.count} role="status">{plural("count.slides", total)}</p>
      ) : null}
      {items && items.length === 0 ? (
        <EmptyState icon="life" title={t("identify.empty.title")}>{t("identify.empty.body")}</EmptyState>
      ) : null}
      {glass.length ? (
        <GlassSet items={glass} name="identify" title={t("identify.title")} label={t("identify.title")} />
      ) : null}
      {items && items.length < total ? (
        <div className={styles.more}>
          <Button busy={loadingMore} onClick={() => void more()}>{t("identify.more", {
            count: Math.min(PAGE, total - items.length) })}</Button>
        </div>
      ) : null}
    </Place>
  );
}
