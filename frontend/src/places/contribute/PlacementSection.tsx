// The fifth section: where the slide goes in the collection. The tree suggests a drawer for the anchor (and its part
// and preservation): its path is shown, drawer by drawer, with every other drawer that accepts it to choose instead.
// A curator may place it elsewhere, with the reason, which the case records.
import { useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { useSession } from "../../account/session";
import { contributeApi } from "../../contribute/api";
import type { CaseDraft } from "../../contribute/draft";
import { worded } from "../../contribute/messages";
import type { PlacementResult } from "../../contract/catalog";
import { useI18n } from "../../i18n";
import { localised, pathTo, useTree } from "../../tree/TreeProvider";
import { Select, TextField } from "../../ui/Field";
import { Skeleton } from "../../ui/Feedback";
import { Glyph, Icon } from "../../ui/Icon";
import styles from "./Contribute.module.css";
import type { SectionProps } from "./sections";

type Answer = { state: "waiting" } | { state: "busy" } | { state: "done"; result: PlacementResult }
  | { state: "failed"; unavailable: boolean };

export function PlacementSection({ draft, update, errorFor }: SectionProps) {
  const { t, lang } = useI18n();
  const tree = useTree();
  const session = useSession();
  const s = draft.specimen;
  const [answer, setAnswer] = useState<Answer>({ state: "waiting" });
  const [overriding, setOverriding] = useState(Boolean(draft.placement.overrideReason));
  const set = (change: Partial<CaseDraft["placement"]>) =>
    update((d) => ({ ...d, placement: { ...d.placement, ...change } }));
  const anchorKey = s.anchor ? `${s.anchor.kind}:${s.anchor.ref}:${s.part}:${s.preservation}` : "";

  useEffect(() => {
    if (!s.anchor) {
      setAnswer({ state: "waiting" });
      return undefined;
    }
    const controller = new AbortController();
    setAnswer({ state: "busy" });
    contributeApi.placement(s.anchor, s.anchor.kind === "taxon" ? s.part || null : null,
      s.anchor.kind === "taxon" ? s.preservation : "recent", controller.signal).then(
      (result) => {
        setAnswer({ state: "done", result });
        // The suggestion is taken unless the contributor chose another drawer that still accepts the slide.
        if (result.suggestion) {
          update((d) => {
            const kept = d.placement.node && (result.accepting ?? []).includes(d.placement.node);
            return kept || d.placement.overrideReason ? d : { ...d, placement: { ...d.placement, node: result.suggestion! } };
          });
        }
      },
      (e: unknown) => {
        if (!controller.signal.aborted) setAnswer({ state: "failed", unavailable: e instanceof ApiError && e.status === 503 });
      });
    return () => controller.abort();
    // The anchor, its part and its preservation name the question.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anchorKey]);

  if (!s.anchor) {
    return <div className={styles.sectionBody}><p className={styles.notice}><Glyph name="info" size={20} />
      <span>{t("placement.needsAnchor")}</span></p></div>;
  }
  if (answer.state === "busy" || answer.state === "waiting" || tree.state !== "ready") {
    return <div className={styles.sectionBody}><Skeleton lines={4} /></div>;
  }
  if (answer.state === "failed") {
    return <div className={styles.sectionBody}><p className={styles.problem} role="alert">
      {answer.unavailable ? t("anchor.unavailable") : t("placement.failed")}</p></div>;
  }
  const result = answer.result;
  const index = tree.tree;
  const name = (id: string) => {
    const node = index.byId.get(id);
    return node ? localised(node.name, lang) : id;
  };
  const accepting = result.accepting ?? [];
  const drawers = [...index.byId.values()].filter((n) => !n.view && n.level !== "realm");

  return (
    <div className={styles.sectionBody}>
      {(result.errors ?? []).map((e, i) => <p key={i} className={styles.problem} role="alert">{worded(t, e)}</p>)}
      {result.suggestion ? (
        <div className={styles.suggestion}>
          <p className={styles.fieldLabel}>{t("placement.suggested")}</p>
          <ol className={styles.path}>
            {pathTo(index, result.suggestion).map((node) => (
              <li key={node.id}><Icon name={node.icon} size={24} /><span>{localised(node.name, lang)}</span></li>
            ))}
          </ol>
        </div>
      ) : null}

      {accepting.length > 1 ? (
        <fieldset className={styles.drawerChoice}>
          <legend className={styles.fieldLabel}>{t("placement.accepting")}</legend>
          {accepting.map((id) => (
            <label key={id} className={styles.drawerOption}>
              <input type="radio" name="placement" value={id} checked={draft.placement.node === id && !overriding}
                onChange={() => { setOverriding(false); set({ node: id, overrideReason: "" }); }} />
              <Icon name={index.byId.get(id)?.icon ?? id} size={24} />
              <span>{pathTo(index, id).map((n) => localised(n.name, lang)).join(" / ")}</span>
              {id === result.suggestion ? <span className={styles.badge}>{t("placement.suggestedBadge")}</span> : null}
            </label>
          ))}
        </fieldset>
      ) : null}
      {errorFor("placement.node") ? <p className={styles.fieldError}>{errorFor("placement.node")}</p> : null}

      {session.can("override_placement") ? (
        <div className={styles.override}>
          <label className={styles.checkLine}>
            <input type="checkbox" checked={overriding} onChange={(e) => {
              setOverriding(e.target.checked);
              if (!e.target.checked) set({ node: result.suggestion ?? "", overrideReason: "" });
            }} />
            <span>{t("placement.override")}</span>
          </label>
          {overriding ? (
            <div className={styles.grid2}>
              <Select label={t("placement.overrideNode")} value={draft.placement.node}
                onChange={(e) => set({ node: e.target.value })}
                options={drawers.map((n) => ({ value: n.id, label: pathTo(index, n.id).map((x) => localised(x.name, lang))
                  .join(" / ") }))} />
              <TextField label={t("placement.overrideReason")} value={draft.placement.overrideReason} maxLength={300}
                error={errorFor("placement.override_reason")} onChange={(e) => set({ overrideReason: e.target.value })} />
            </div>
          ) : null}
        </div>
      ) : null}
      <p className={styles.fieldHint}>{t("placement.chosen", { name: draft.placement.node ? name(draft.placement.node)
        : t("placement.none") })}</p>
    </div>
  );
}
