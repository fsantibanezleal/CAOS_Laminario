// The two small forms of the community: a flag (a category and a comment, by any signed-in account) and a curator's
// reason for hiding or restoring (at least 10 characters, as iNaturalist asks of its curators). Each is the
// interface's modal dialog; a refusal is said inside it.
import { useEffect, useId, useState } from "react";
import { ApiError } from "../api/client";
import { useI18n } from "../i18n";
import type { MessageKey } from "../i18n/en";
import { Button } from "../ui/Button";
import { RadioGroup } from "../ui/Choice";
import { Dialog } from "../ui/Overlay";
import { communityApi, FLAG_CATEGORIES, MIN_REASON, type FlagCategory, type TargetKind } from "./api";
import styles from "./Community.module.css";

function said(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.reason ?? fallback;
  return fallback;
}

export function TextArea({ label, value, onChange, hint, error, maxLength, rows = 4 }: { label: string; value: string;
  onChange: (value: string) => void; hint?: string; error?: string; maxLength?: number; rows?: number }) {
  const id = useId();
  return (
    <div className={styles.field} data-invalid={error ? "true" : undefined}>
      <label className={styles.fieldLabel} htmlFor={id}>{label}</label>
      <textarea id={id} className={styles.textarea} rows={rows} value={value} maxLength={maxLength}
        aria-invalid={error ? true : undefined}
        aria-describedby={[hint ? `${id}-hint` : "", error ? `${id}-error` : ""].filter(Boolean).join(" ") || undefined}
        onChange={(e) => onChange(e.target.value)} />
      {hint ? <p id={`${id}-hint`} className={styles.hint}>{hint}</p> : null}
      {error ? <p id={`${id}-error`} className={styles.error}>{error}</p> : null}
    </div>
  );
}

export function FlagDialog({ open, kind, id, onClose, onDone }: { open: boolean; kind: TargetKind; id: string;
  onClose: () => void; onDone: () => void }) {
  const { t } = useI18n();
  const [category, setCategory] = useState<FlagCategory>("wrong");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  useEffect(() => {
    if (open) {
      setCategory("wrong");
      setComment("");
      setProblem(null);
    }
  }, [open]);

  const submit = async () => {
    setBusy(true);
    setProblem(null);
    try {
      await communityApi.flag(kind, id, category, comment.trim() || null);
      onDone();
    } catch (e) {
      setProblem(said(e, t("account.error.server")));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} title={t(`flag.title.${kind}`)} onClose={onClose} actions={<>
      <Button onClick={onClose}>{t("action.cancel")}</Button>
      <Button variant="primary" icon="warning" busy={busy} onClick={() => void submit()}>{t("flag.send")}</Button>
    </>}>
      <div className={styles.dialogBody}>
        <p className={styles.hint}>{t("flag.lead")}</p>
        <RadioGroup legend={t("flag.category")} value={category} onChange={setCategory}
          options={FLAG_CATEGORIES.map((c) => ({ value: c, label: <span className={styles.option}>
            <strong>{t(`flag.category.${c}` as MessageKey)}</strong>
            <span>{t(`flag.category.${c}.about` as MessageKey)}</span></span> }))} />
        <TextArea label={t("flag.comment")} value={comment} onChange={setComment} maxLength={1000} rows={3} />
        {problem ? <p className={styles.error} role="alert">{problem}</p> : null}
      </div>
    </Dialog>
  );
}

export function ReasonDialog({ open, action, kind, id, onClose, onDone }: { open: boolean; action: "hide" | "unhide";
  kind: TargetKind; id: string; onClose: () => void; onDone: () => void }) {
  const { t } = useI18n();
  const [reason, setReason] = useState("");
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  useEffect(() => {
    if (open) {
      setReason("");
      setTried(false);
      setProblem(null);
    }
  }, [open]);
  const short = reason.trim().length < MIN_REASON;

  const submit = async () => {
    setTried(true);
    if (short) return;
    setBusy(true);
    setProblem(null);
    try {
      await (action === "hide" ? communityApi.hide(kind, id, reason.trim()) : communityApi.unhide(kind, id, reason.trim()));
      onDone();
    } catch (e) {
      setProblem(e instanceof ApiError && e.status === 403 ? t("moderate.notYours") : said(e, t("account.error.server")));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} title={t(`moderate.${action}.title.${kind}`)} onClose={onClose} actions={<>
      <Button onClick={onClose}>{t("action.cancel")}</Button>
      <Button variant={action === "hide" ? "danger" : "primary"} busy={busy} onClick={() => void submit()}>
        {t(`moderate.${action}`)}</Button>
    </>}>
      <div className={styles.dialogBody}>
        <p className={styles.hint}>{t(`moderate.${action}.lead`)}</p>
        <TextArea label={t("moderate.reason")} value={reason} onChange={setReason} maxLength={2000}
          hint={t("moderate.reason.hint", { count: MIN_REASON })}
          error={tried && short ? t("moderate.reason.short", { count: MIN_REASON }) : undefined} />
        {problem ? <p className={styles.error} role="alert">{problem}</p> : null}
      </div>
    </Dialog>
  );
}
