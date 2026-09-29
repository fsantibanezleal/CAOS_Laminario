// A slide's identifications (U13): what the community agrees on and how it got there (every identification that
// counted, the score of the agreed node against the two-thirds it had to exceed), the identifications themselves
// with their category, the form an identifier adds one with, the vote on whether the name can still be improved,
// and the flags and the curators' hiding and restoring. Loaded as its own chunk on the slide place.
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "wouter";
import { useSession } from "../account/session";
import { ApiError } from "../api/client";
import type { AnchorRecord, IdentificationList, IdentificationRecord, SlideRecord } from "../contract/catalog";
import type { Anchor } from "../contract/ingest";
import { known, rankName } from "../contribute/messages";
import { useI18n } from "../i18n";
import type { MessageKey } from "../i18n/en";
import { AnchorField } from "../places/contribute/AnchorField";
import { AnchorName } from "../places/contribute/AnchorName";
import { Button } from "../ui/Button";
import { RadioGroup } from "../ui/Choice";
import { Skeleton } from "../ui/Feedback";
import { Glyph, Icon } from "../ui/Icon";
import { useToast } from "../ui/Overlay";
import { communityApi, type TargetKind } from "./api";
import styles from "./Community.module.css";
import { FlagDialog, ReasonDialog, TextArea } from "./Dialogs";

const KINDS = ["taxon", "rock", "mineral", "crystal", "material"] as const;
const KIND_ICONS: Record<Anchor["kind"], string> = { taxon: "life", rock: "earth.rocks", mineral: "earth.minerals",
  crystal: "matter.crystals", material: "matter.materials" };

type Dialogs = { flag: { kind: TargetKind; id: string } | null;
  reason: { action: "hide" | "unhide"; kind: TargetKind; id: string } | null };

function Meter({ score, cutoff }: { score: number; cutoff: number }) {
  const { t, number } = useI18n();
  return (
    <div className={styles.meter} role="img" aria-label={t("community.meter", { score: number(score, {
      style: "percent", maximumFractionDigits: 0 }), cutoff: number(cutoff, { style: "percent",
      maximumFractionDigits: 0 }) })}>
      <span className={styles.meterFill} style={{ width: `${Math.round(score * 100)}%` }} />
      <span className={styles.meterCut} style={{ left: `${cutoff * 100}%` }} />
    </div>
  );
}

function AnchorLine({ anchor }: { anchor: AnchorRecord }) {
  const { t } = useI18n();
  return (
    <span className={styles.anchorLine}>
      <AnchorName kind={anchor.kind} rank={anchor.rank} name={anchor.name} />
      {anchor.rank ? <span className={styles.rank}>{rankName(t, anchor.rank)}</span> : null}
    </span>
  );
}

export function IdentificationsPanel({ record, onHidden, onChanged }: { record: SlideRecord;
  onHidden?: () => void; onChanged?: () => void }) {
  const { t, date } = useI18n();
  const session = useSession();
  const toast = useToast();
  const [, navigate] = useLocation();
  const [data, setData] = useState<IdentificationList | null>(null);
  const shown = useRef<IdentificationList | null>(null);
  const [failed, setFailed] = useState(false);
  const [dialogs, setDialogs] = useState<Dialogs>({ flag: null, reason: null });
  const [kind, setKind] = useState<Anchor["kind"]>(record.anchor.kind);
  const [anchor, setAnchor] = useState<Anchor | null>(null);
  const [body, setBody] = useState("");
  const [askDisagreement, setAskDisagreement] = useState(false);
  const [disagreement, setDisagreement] = useState<"yes" | "no">("no");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const canIdentify = session.can("identify");
  const canModerate = session.can("moderate");

  const load = useCallback(async () => {
    try {
      const next = await communityApi.identifications(record.id);
      const before = shown.current;
      shown.current = next;
      setData(next);
      setFailed(false);
      // The badge or the anchor moved: the slide around this panel is read again.
      if (before && (before.community.badge !== next.community.badge
        || before.community.node !== next.community.node)) onChanged?.();
    } catch {
      setFailed(true);
    }
    // The callback is the slide place's; the slide's id names what is read.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [record.id]);

  useEffect(() => {
    void load();
  }, [load, session.account]);

  const submit = async () => {
    if (!anchor) return;
    setBusy(true);
    setProblem(null);
    try {
      await communityApi.identify(record.id, anchor, body.trim() || null,
        askDisagreement ? disagreement === "yes" : null);
      setAnchor(null);
      setBody("");
      setAskDisagreement(false);
      toast.show(t("community.added"), "good");
      await load();
    } catch (e) {
      if (e instanceof ApiError && e.code === "disagreement_unstated") {
        setAskDisagreement(true);
      } else if (e instanceof ApiError && e.code) {
        const key = `validation.${e.code}`;
        setProblem(known(key) ? t(key) : e.reason ?? t("account.error.server"));
      } else {
        setProblem(t("account.error.server"));
      }
    } finally {
      setBusy(false);
    }
  };

  const act = async (work: () => Promise<unknown>, done: string) => {
    try {
      await work();
      toast.show(done, "good");
      await load();
    } catch {
      toast.show(t("account.error.server"), "bad");
    }
  };

  if (failed) return <p className={styles.error} role="alert">{t("community.failed")}</p>;
  if (!data) return <Skeleton lines={4} />;
  const c = data.community;
  const supporting = c.node ? (c.scores ?? []).find((s) => s.node === c.node) : null;

  return (
    <div className={styles.panel}>
      <div className={styles.agreement} data-badge={c.badge}>
        {c.node ? (
          <>
            <p className={styles.agreeLead}>{t("community.agrees")}</p>
            <p className={styles.agreeName}>{c.anchor ? <AnchorLine anchor={c.anchor} /> : c.node}</p>
            {supporting && c.score !== null && c.score !== undefined ? (
              <>
                <Meter score={c.score} cutoff={c.cutoff} />
                <p className={styles.hint}>{t("community.support", { agree: supporting.cumulative,
                  all: supporting.cumulative + supporting.disagreements + supporting.ancestor_disagreements })}</p>
              </>
            ) : null}
          </>
        ) : (
          <p className={styles.agreeLead}>{c.identifications < 2 ? t("community.none.few") : t("community.none.split")}</p>
        )}
        <p className={styles.badgeLine}><Glyph name={c.badge === "verified" ? "check" : c.badge === "reference" ? "info"
          : "search"} size={20} /><span><strong>{t(`quality.${c.badge}` as MessageKey)}</strong>
          {" "}{t(`community.badge.${c.badge}`)}</span></p>
        {c.node && canIdentify ? (
          <div className={styles.vote}>
            <p className={styles.fieldLabel}>{t("community.vote.question")}</p>
            <div className={styles.voteRow}>
              <Button size="small" variant={c.my_vote === true ? "primary" : "secondary"} aria-pressed={c.my_vote === true}
                onClick={() => void act(() => communityApi.vote(record.id, c.my_vote === true ? null : true),
                  t("community.vote.saved"))}>
                {t("community.vote.asGood", { count: c.as_good_as_it_can_be ?? 0 })}</Button>
              <Button size="small" variant={c.my_vote === false ? "primary" : "secondary"}
                aria-pressed={c.my_vote === false}
                onClick={() => void act(() => communityApi.vote(record.id, c.my_vote === false ? null : false),
                  t("community.vote.saved"))}>
                {t("community.vote.needsMore", { count: c.needs_more ?? 0 })}</Button>
            </div>
          </div>
        ) : null}
      </div>

      <ol className={styles.list}>
        {data.identifications.map((i: IdentificationRecord) => (
          <li key={i.id} className={styles.item} data-current={i.current || undefined} data-hidden={i.hidden || undefined}>
            <div className={styles.itemHead}>
              <Icon name={KIND_ICONS[i.anchor.kind]} size={24} />
              <AnchorLine anchor={i.anchor} />
              {i.category ? <span className={styles.category} data-category={i.category}>
                {t(`community.category.${i.category}`)}</span> : null}
            </div>
            <p className={styles.meta}>
              <span>{i.source ? t("community.bySource") : i.by_handle && i.by
                ? <Link href={`/people/${i.by_handle}`}>{i.by}</Link> : i.by ?? t("community.byUnknown")}</span>
              <span>{date(i.created_at, { dateStyle: "medium" })}</span>
              {!i.current ? <span className={styles.muted}>{t("community.withdrawn")}</span> : null}
              {i.hidden ? <span className={styles.warn}>{t("community.hidden")}</span> : null}
              {i.disagreement ? <span className={styles.warn}>{t("community.disagrees")}</span> : null}
            </p>
            {i.body ? <p className={styles.body}>{i.body}</p> : null}
            <div className={styles.actions}>
              {i.mine && i.current ? (
                <Button size="small" variant="quiet" onClick={() => void act(() => communityApi.withdraw(i.id),
                  t("community.withdrawn.done"))}>{t("community.withdraw")}</Button>
              ) : null}
              {i.mine && !i.current && !i.hidden ? (
                <Button size="small" variant="quiet" onClick={() => void act(() => communityApi.restore(i.id),
                  t("community.restored.done"))}>{t("community.restore")}</Button>
              ) : null}
              {session.account && !i.mine && !i.hidden ? (
                <Button size="small" variant="quiet" icon="warning"
                  onClick={() => setDialogs({ ...dialogs, flag: { kind: "identification", id: i.id } })}>
                  {t("flag.open")}</Button>
              ) : null}
              {canModerate ? (
                <Button size="small" variant="quiet" onClick={() => setDialogs({ ...dialogs, reason: {
                  action: i.hidden ? "unhide" : "hide", kind: "identification", id: i.id } })}>
                  {i.hidden ? t("moderate.unhide") : t("moderate.hide")}</Button>
              ) : null}
            </div>
          </li>
        ))}
      </ol>

      {canIdentify ? (
        <form className={styles.form} onSubmit={(e) => { e.preventDefault(); void submit(); }}>
          <h3 className={styles.formTitle}>{t("community.add")}</h3>
          <RadioGroup legend={t("specimen.kind")} value={kind} inline onChange={(k) => { setKind(k); setAnchor(null); }}
            options={KINDS.map((k) => ({ value: k, label: t(`anchor.kind.${k}`) }))} />
          <AnchorField kind={kind} value={anchor} onChange={(a) => { setAnchor(a); setAskDisagreement(false); }}
            label={t(`anchor.label.${kind}`)} hint={t(`anchor.hint.${kind}`)} />
          <TextArea label={t("community.comment")} value={body} onChange={setBody} maxLength={1000} rows={3}
            hint={t("community.comment.hint")} />
          {askDisagreement ? (
            <div className={styles.question} role="group" aria-labelledby="disagree-q">
              <p id="disagree-q" className={styles.fieldLabel}>{t("community.disagree.question", {
                name: record.anchor.name })}</p>
              <RadioGroup legend={t("community.disagree.legend")} value={disagreement} onChange={setDisagreement}
                options={[{ value: "no", label: t("community.disagree.no") },
                  { value: "yes", label: t("community.disagree.yes", { name: record.anchor.name }) }]} />
            </div>
          ) : null}
          {problem ? <p className={styles.error} role="alert">{problem}</p> : null}
          <Button type="submit" variant="primary" icon="check" busy={busy} disabled={!anchor}>
            {t("community.submit")}</Button>
        </form>
      ) : !session.account ? (
        <p className={styles.hint}>{t("community.signInToIdentify")}</p>
      ) : (
        <p className={styles.hint}>{t("community.identifiersOnly")}</p>
      )}

      {session.account ? (
        <div className={styles.slideActions}>
          <Button size="small" variant="quiet" icon="warning"
            onClick={() => setDialogs({ ...dialogs, flag: { kind: "slide", id: record.id } })}>
            {t("flag.open.slide")}</Button>
          {canModerate ? (
            <Button size="small" variant="danger"
              onClick={() => setDialogs({ ...dialogs, reason: { action: "hide", kind: "slide", id: record.id } })}>
              {t("moderate.hide.slide")}</Button>
          ) : null}
        </div>
      ) : null}

      <FlagDialog open={dialogs.flag !== null} kind={dialogs.flag?.kind ?? "slide"} id={dialogs.flag?.id ?? ""}
        onClose={() => setDialogs({ ...dialogs, flag: null })}
        onDone={() => { setDialogs({ ...dialogs, flag: null }); toast.show(t("flag.sent"), "good"); }} />
      <ReasonDialog open={dialogs.reason !== null} action={dialogs.reason?.action ?? "hide"}
        kind={dialogs.reason?.kind ?? "slide"} id={dialogs.reason?.id ?? ""}
        onClose={() => setDialogs({ ...dialogs, reason: null })}
        onDone={() => {
          const done = dialogs.reason;
          setDialogs({ ...dialogs, reason: null });
          if (done?.kind === "slide" && done.action === "hide") {
            toast.show(t("moderate.hidden.slide"), "good");
            onHidden?.();
            navigate("/moderate");
          } else {
            toast.show(done?.action === "hide" ? t("moderate.hidden") : t("moderate.restored"), "good");
            void load();
          }
        }} />
    </div>
  );
}
