// The last section: the case read back as a whole, what still stops it (each message with the way to its field) and
// what the server only notes; then the case stored as a draft; then its files, sent with their progress and followed
// through verification and processing; then submission, and the publication (R-1205, R-1208).
import { Link } from "wouter";
import type { CaseRecord, ValidationError, ValidationFlag } from "../../contract/catalog";
import { sectionOf, type CaseDraft } from "../../contribute/draft";
import { worded } from "../../contribute/messages";
import { pending } from "../../contribute/pending";
import { useI18n } from "../../i18n";
import { Button } from "../../ui/Button";
import { Progress } from "../../ui/Feedback";
import { Glyph } from "../../ui/Icon";
import styles from "./Contribute.module.css";
import { bytes } from "./ImageCard";
import type { Step } from "./sections";
import { allFiles, type JobStep, type useCaseFiles } from "./useCaseFiles";

interface SendSectionProps {
  draft: CaseDraft;
  record: CaseRecord | null;
  errors: ValidationError[];
  flags: ValidationFlag[];
  checking: boolean;
  dirty: boolean;
  saving: boolean;
  saveProblem: string | null;
  submitting: boolean;
  onSave: () => void;
  onSubmit: () => void;
  goTo: (step: Step, field?: string) => void;
  files: ReturnType<typeof useCaseFiles>;
}

function stepWords(t: ReturnType<typeof useI18n>["t"], step: JobStep | undefined): string | null {
  if (!step) return null;
  if (step.event === "failed") return t("send.step.failed");
  if (step.kind === "verify") {
    if (step.step === "checksum") return t("send.step.checksum");
    if (step.step === "sniffed") return t("send.step.sniffed", { kind: String(step.detail.kind ?? "") });
    if (step.step === "readable") return t("send.step.readable");
    if (step.step === "accepted") return t("send.step.accepted");
    if (step.step === "rejected") return t("send.step.rejected");
    return t("send.step.verifying");
  }
  if (step.event === "succeeded") return t("send.step.processed");
  if (step.step === "read") return t("send.step.read");
  if (step.step === "pyramid") return t("send.step.pyramid");
  if (step.step === "stored") return t("send.step.stored");
  return t("send.step.processing");
}

export function SendSection({ draft, record, errors, flags, checking, dirty, saving, saveProblem, submitting, onSave,
  onSubmit, goTo, files }: SendSectionProps) {
  const { t, lang, number } = useI18n();
  const status = record?.status ?? null;
  const images = record?.images ?? [];
  const everyFile = allFiles(record);
  const canSubmit = status === "draft" && everyFile && !dirty && errors.length === 0;

  if (status === "published" && record) {
    return (
      <div className={styles.sectionBody}>
        <div className={styles.published} role="status">
          <Glyph name="check" size={32} />
          <div>
            <p className={styles.publishedTitle}>{t("send.published")}</p>
            <p>{t("send.published.body", { id: record.id })}</p>
            <Link href={`/s/${record.id}`} className={styles.primaryLink}><Glyph name="slide" size={20} />
              <span>{t("send.open")}</span></Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.sectionBody}>
      <section aria-labelledby="review-title" className={styles.review}>
        <h3 id="review-title" className={styles.subTitle}>{t("send.review")}</h3>
        {checking ? <p className={styles.fieldHint}>{t("send.checking")}</p> : null}
        {errors.length === 0 && !checking ? (
          <p className={styles.okLine}><Glyph name="check" size={20} /><span>{t("send.noErrors")}</span></p>
        ) : null}
        {errors.length ? (
          <ul className={styles.messageList}>
            {errors.map((e, i) => (
              <li key={`${e.field}-${i}`}>
                <Glyph name="warning" size={16} />
                <span><strong>{t(`step.${sectionOf(e.field)}`)}</strong>: {worded(t, e)}</span>
                <button type="button" className={styles.linkButton} onClick={() => goTo(sectionOf(e.field), e.field)}>
                  {t("send.goTo")}</button>
              </li>
            ))}
          </ul>
        ) : null}
        {flags.length ? (
          <ul className={styles.messageList} data-kind="flags">
            {flags.map((f, i) => (
              <li key={`${f.field}-${i}`}><Glyph name="info" size={16} /><span>{worded(t, f)}</span></li>
            ))}
          </ul>
        ) : null}
      </section>

      {status === null || status === "draft" ? (
        <div className={styles.saveRow}>
          <Button variant={record ? "secondary" : "primary"} icon="draft" busy={saving}
            disabled={saving || (!!record && !dirty)} onClick={onSave}>
            {record ? (dirty ? t("send.saveChanges") : t("send.saved")) : t("send.saveDraft")}
          </Button>
          <p className={styles.fieldHint}>{record ? t("send.draftHint", { id: record.id }) : t("send.saveHint")}</p>
          {saveProblem ? <p className={styles.problem} role="alert">{saveProblem}</p> : null}
        </div>
      ) : null}

      {record ? (
        <section aria-labelledby="files-title" className={styles.files}>
          <h3 id="files-title" className={styles.subTitle}>{t("send.files")}</h3>
          {status === "draft" && record.status_reason ? (
            <p className={styles.problem} role="alert">{record.status_reason}</p>
          ) : null}
          <ul className={styles.fileList}>
            {images.map((image) => {
              const token = image.token ?? "";
              const local = pending.get(token);
              const up = files.progress[token];
              const step = files.steps[token];
              const draftImage = draft.images.find((i) => i.token === token);
              const name = draftImage?.source === "iiif" ? t("images.iiif") : local?.name ?? draftImage?.fileName
                ?? t("images.noFile");
              let state: string;
              let tone: "ok" | "warn" | "bad" | "busy" = "busy";
              if (image.status === "ready") { state = t("send.state.ready"); tone = "ok"; }
              else if (image.status === "failed") { state = image.failure ?? t("send.state.failed"); tone = "bad"; }
              else if (image.upload_status === "rejected" && !up) { state = image.upload_reason ?? t("send.state.rejected"); tone = "bad"; }
              else if (up?.state === "failed") { state = up.error ?? t("send.state.uploadFailed"); tone = "bad"; }
              else if (up && (up.state === "uploading" || up.state === "paused" || up.state === "waiting")) {
                state = up.state === "paused" ? t("send.state.paused") : t("send.state.sending");
              } else if (image.has_file && status === "processing") {
                state = stepWords(t, step) ?? t("send.step.processing");
              } else if (image.has_file) { state = t("send.state.accepted"); tone = "ok"; }
              else if (image.upload_status === "received" || up?.state === "sent") {
                state = stepWords(t, step) ?? t("send.step.verifying");
              } else if (local) { state = t("send.state.readyToSend", { size: bytes(local.size, lang) }); tone = "warn"; }
              else { state = t("send.state.needsFile"); tone = "warn"; }
              const fraction = up && up.total ? up.sent / up.total : undefined;
              return (
                <li key={image.asset_id} className={styles.fileRowItem} data-tone={tone}>
                  <Glyph name={image.family === "macro" ? "camera" : "objective"} size={24} />
                  <div className={styles.fileText}>
                    <p className={styles.fileName}>{name}</p>
                    <p className={styles.fileState}>{state}</p>
                    {files.stripped[token] ? <p className={styles.fieldHint}>{t("send.stripped")}</p> : null}
                    {up && (up.state === "uploading" || up.state === "paused") && fraction !== undefined ? (
                      <Progress label={t("send.progress", { sent: bytes(up.sent, lang), total: bytes(up.total, lang) })}
                        value={fraction} />
                    ) : null}
                  </div>
                  <div className={styles.fileActions}>
                    {up && (up.state === "uploading" || up.state === "paused") ? (
                      <Button size="small" variant="quiet" icon={up.state === "paused" ? "play" : "pause"}
                        onClick={() => files.pauseResume(token)}>
                        {up.state === "paused" ? t("send.resume") : t("send.pause")}</Button>
                    ) : null}
                    {up?.state === "failed" ? (
                      <Button size="small" variant="quiet" icon="retry" onClick={() => void files.retry(token)}>
                        {t("send.retry")}</Button>
                    ) : null}
                    {(tone === "bad" || (!local && !image.has_file)) && status === "draft" ? (
                      <button type="button" className={styles.linkButton} onClick={() => goTo("images")}>
                        {t("send.chooseAgain")}</button>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
          {status === "draft" ? (
            <div className={styles.saveRow}>
              <Button icon="upload" busy={files.sending} disabled={files.sending || files.waiting.length === 0 || dirty}
                onClick={() => void files.send()}>
                {t("send.sendFiles", { count: number(files.waiting.length) })}</Button>
              <Button variant="primary" icon="check" busy={submitting} disabled={!canSubmit || submitting}
                onClick={onSubmit}>{t("send.submit")}</Button>
              <p className={styles.fieldHint}>{dirty ? t("send.saveFirst") : everyFile ? t("send.submitHint")
                : t("send.filesFirst")}</p>
            </div>
          ) : null}
          {status === "processing" ? (
            <p className={styles.notice} role="status"><Glyph name="clock" size={20} />
              <span>{t("send.processing")}</span></p>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
