// /moderate: the curators' place (R-1305, R-1306). The open flags, each with what it points at, resolved with a comment
// or acted on (the item hidden with a reason); the items hidden now, each restorable by the curator who hid it or an
// admin; and the log of every hiding and restoring. A visitor is sent to sign in; an account without the capability
// is told so.
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "wouter";
import { signInHref } from "../../account/api";
import { useSession } from "../../account/session";
import { communityApi, type TargetKind } from "../../community/api";
import { ReasonDialog, TextArea } from "../../community/Dialogs";
import type { FlagRecord, ModerationActionRecord } from "../../contract/catalog";
import { useI18n } from "../../i18n";
import type { MessageKey } from "../../i18n/en";
import { Place } from "../../router/Place";
import { Button } from "../../ui/Button";
import { EmptyState, Skeleton } from "../../ui/Feedback";
import { Tabs } from "../../ui/Tabs";
import { useToast } from "../../ui/Overlay";
import styles from "./Identify.module.css";

type Tab = "flags" | "hidden" | "log";

function FlagItem({ flag, onChanged, onHide }: { flag: FlagRecord; onChanged: () => void;
  onHide: (kind: TargetKind, id: string, hidden: boolean) => void }) {
  const { t, date } = useI18n();
  const toast = useToast();
  const [resolving, setResolving] = useState(false);
  const [resolution, setResolution] = useState("");
  const [busy, setBusy] = useState(false);
  const resolve = async () => {
    if (!resolution.trim()) return;
    setBusy(true);
    try {
      await communityApi.resolve(flag.id, resolution.trim());
      toast.show(t("moderate.resolved"), "good");
      onChanged();
    } catch {
      toast.show(t("account.error.server"), "bad");
    } finally {
      setBusy(false);
    }
  };
  return (
    <li className={styles.flag} data-resolved={flag.resolved_at ? "" : undefined}>
      <p className={styles.flagHead}>
        <span className={styles.flagTitle}>{t(`flag.category.${flag.category}` as MessageKey)}</span>
        <span className={styles.chip}>{t(`moderate.target.${flag.target_kind}`)}</span>
        <Link href={`/s/${flag.slide_id}`}>{flag.slide_name} <span>({flag.slide_id})</span></Link>
        {flag.hidden ? <span className={styles.chip}>{t("community.hidden")}</span> : null}
      </p>
      <p className={styles.flagMeta}>
        <span>{t("moderate.flaggedBy", { name: flag.by ?? "" })}</span>
        <span>{date(flag.created_at, { dateStyle: "medium", timeStyle: "short" })}</span>
        {flag.resolved_at ? <span>{t("moderate.resolvedBy", { name: flag.resolved_by ?? "",
          when: date(flag.resolved_at, { dateStyle: "medium" }) })}</span> : null}
      </p>
      {flag.comment ? <p className={styles.flagComment}>{flag.comment}</p> : null}
      {flag.resolution ? <p className={styles.flagComment}><strong>{t("moderate.resolution")}:</strong> {flag.resolution}</p>
        : null}
      {!flag.resolved_at ? (
        <div className={styles.flagActions}>
          {resolving ? (
            <div className={styles.resolveForm}>
              <TextArea label={t("moderate.resolution")} value={resolution} onChange={setResolution} maxLength={1000}
                rows={2} />
              <div className={styles.flagActions}>
                <Button size="small" onClick={() => setResolving(false)}>{t("action.cancel")}</Button>
                <Button size="small" variant="primary" busy={busy} disabled={!resolution.trim()}
                  onClick={() => void resolve()}>{t("moderate.resolve")}</Button>
              </div>
            </div>
          ) : (
            <>
              <Button size="small" onClick={() => setResolving(true)}>{t("moderate.resolve")}</Button>
              <Button size="small" variant={flag.hidden ? "secondary" : "danger"}
                onClick={() => onHide(flag.target_kind, flag.target_kind === "slide" ? flag.slide_id : flag.target_id,
                  Boolean(flag.hidden))}>
                {flag.hidden ? t("moderate.unhide") : t(`moderate.hide.${flag.target_kind}`)}</Button>
            </>
          )}
        </div>
      ) : null}
    </li>
  );
}

function ActionTable({ actions, onRestore }: { actions: ModerationActionRecord[];
  onRestore?: (a: ModerationActionRecord) => void }) {
  const { t, date } = useI18n();
  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th scope="col">{t("moderate.when")}</th>
          <th scope="col">{t("moderate.action")}</th>
          <th scope="col">{t("moderate.item")}</th>
          <th scope="col">{t("moderate.reason")}</th>
          <th scope="col">{t("moderate.by")}</th>
          {onRestore ? <th scope="col"><span className="visually-hidden">{t("moderate.unhide")}</span></th> : null}
        </tr>
      </thead>
      <tbody>
        {actions.map((a, i) => (
          <tr key={`${a.target_kind}-${a.target_id}-${i}`}>
            <td data-label={t("moderate.when")}>{date(a.created_at, { dateStyle: "medium", timeStyle: "short" })}</td>
            <td data-label={t("moderate.action")}>{t(`moderate.action.${a.action}`)}</td>
            <td data-label={t("moderate.item")}>{t(`moderate.target.${a.target_kind}`)}{" "}
              <Link href={`/s/${a.slide_id}`}>{a.slide_id}</Link></td>
            <td data-label={t("moderate.reason")}>{a.reason}</td>
            <td data-label={t("moderate.by")}>{a.by ?? ""}</td>
            {onRestore ? <td data-label="">
              <Button size="small" onClick={() => onRestore(a)}>{t("moderate.unhide")}</Button></td> : null}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function ModeratePlace() {
  const { t } = useI18n();
  const session = useSession();
  const [location, navigate] = useLocation();
  const [tab, setTab] = useState<Tab>("flags");
  const [status, setStatus] = useState<"open" | "resolved">("open");
  const [flags, setFlags] = useState<FlagRecord[] | null>(null);
  const [hidden, setHidden] = useState<ModerationActionRecord[] | null>(null);
  const [log, setLog] = useState<ModerationActionRecord[] | null>(null);
  const [dialog, setDialog] = useState<{ action: "hide" | "unhide"; kind: TargetKind; id: string } | null>(null);
  const toast = useToast();

  useEffect(() => {
    if (session.state === "ready" && !session.account) navigate(signInHref(location), { replace: true });
  }, [session.state, session.account, location, navigate]);

  const load = useCallback(async () => {
    if (!session.can("moderate")) return;
    const [f, h, l] = await Promise.all([communityApi.flags(status), communityApi.hidden(), communityApi.actions()]);
    setFlags(f);
    setHidden(h);
    setLog(l);
  }, [session, status]);

  useEffect(() => {
    void load();
  }, [load]);

  if (session.state !== "ready" || !session.account) {
    return <Place title={t("moderate.title")} ready={false}><Skeleton lines={4} /></Place>;
  }
  if (!session.can("moderate")) {
    return (
      <Place title={t("moderate.title")}>
        <EmptyState icon="life" title={t("moderate.notAllowed.title")}>{t("moderate.notAllowed.body")}</EmptyState>
      </Place>
    );
  }

  const flagsPanel = flags === null ? <Skeleton lines={4} /> : (
    <>
      <div className={styles.flagActions}>
        <Button size="small" variant={status === "open" ? "primary" : "secondary"} aria-pressed={status === "open"}
          onClick={() => setStatus("open")}>{t("moderate.open")}</Button>
        <Button size="small" variant={status === "resolved" ? "primary" : "secondary"}
          aria-pressed={status === "resolved"} onClick={() => setStatus("resolved")}>{t("moderate.resolvedTab")}</Button>
      </div>
      {flags.length === 0 ? (
        <EmptyState icon="life" title={t(`moderate.empty.${status}`)}>{t("moderate.empty.body")}</EmptyState>
      ) : (
        <ul className={styles.flagList}>
          {flags.map((f) => <FlagItem key={f.id} flag={f} onChanged={() => void load()}
            onHide={(kind, id, isHidden) => setDialog({ action: isHidden ? "unhide" : "hide", kind, id })} />)}
        </ul>
      )}
    </>
  );

  return (
    <Place title={t("moderate.title")} ready={flags !== null} wide>
      <p className={styles.lead}>{t("moderate.lead")}</p>
      <div className={styles.tabs}>
        <Tabs label={t("moderate.title")} selected={tab} onSelect={setTab} items={[
          { key: "flags", label: t("moderate.tab.flags", { count: flags?.filter((f) => !f.resolved_at).length ?? 0 }),
            panel: flagsPanel },
          { key: "hidden", label: t("moderate.tab.hidden", { count: hidden?.length ?? 0 }), panel: hidden === null
            ? <Skeleton lines={3} /> : hidden.length === 0
              ? <EmptyState icon="life" title={t("moderate.hidden.none")}>{t("moderate.hidden.none.body")}</EmptyState>
              : <ActionTable actions={hidden} onRestore={(a) => setDialog({ action: "unhide", kind: a.target_kind,
                id: a.target_id })} /> },
          { key: "log", label: t("moderate.tab.log"), panel: log === null ? <Skeleton lines={3} />
            : log.length === 0 ? <p>{t("moderate.log.none")}</p> : <ActionTable actions={log} /> },
        ]} />
      </div>
      <ReasonDialog open={dialog !== null} action={dialog?.action ?? "hide"} kind={dialog?.kind ?? "slide"}
        id={dialog?.id ?? ""} onClose={() => setDialog(null)} onDone={() => {
          toast.show(dialog?.action === "hide" ? t("moderate.hidden") : t("moderate.restored"), "good");
          setDialog(null);
          void load();
        }} />
    </Place>
  );
}
