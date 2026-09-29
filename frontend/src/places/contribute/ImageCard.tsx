// One image of the case: its file (or IIIF service), what its photograph says, its role, its licence and its
// author, and for a micro image how it was lit, its pixel size (typed, or calibrated on a stage micrometer: R-1207),
// and its place in a focal stack or a polarised pair.
import { useRef, useState } from "react";
import { written } from "../../contribute/calibration";
import { LICENCES, MODALITIES, ROLES_BY_FAMILY, type CaseDraft, type ImageDraft } from "../../contribute/draft";
import { pending } from "../../contribute/pending";
import { useI18n } from "../../i18n";
import { localised, useTree } from "../../tree/TreeProvider";
import { Button, IconButton } from "../../ui/Button";
import { Select, TextField } from "../../ui/Field";
import { Glyph } from "../../ui/Icon";
import { Calibrator } from "./Calibrator";
import styles from "./Contribute.module.css";
import { useThumbnail } from "./ImagesSection";
import type { ErrorOptions } from "./sections";

interface ImageCardProps {
  image: ImageDraft;
  index: number;
  count: number;
  draft: CaseDraft;
  hasFile: boolean;
  onChange: (change: Partial<ImageDraft>) => void;
  onRemove: () => void;
  onMove: (by: -1 | 1) => void;
  onReplaceFile: (file: File) => void;
  onUsePosition: (lat: number, lon: number) => void;
  errorFor: (path: string, options?: ErrorOptions) => string | undefined;
  flagFor: (path: string, options?: ErrorOptions) => string | undefined;
}

export function bytes(n: number, lang: string): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let v = n;
  let u = 0;
  while (v >= 1000 && u < units.length - 1) {
    v /= 1000;
    u += 1;
  }
  return `${new Intl.NumberFormat(lang, { maximumFractionDigits: v < 10 && u ? 1 : 0 }).format(v)} ${units[u]}`;
}

export function ImageCard({ image, index, count, draft, hasFile, onChange, onRemove, onMove, onReplaceFile,
  onUsePosition, errorFor, flagFor }: ImageCardProps) {
  const { t, lang, date } = useI18n();
  const tree = useTree();
  const at = `assets.${index}`;
  const fileInput = useRef<HTMLInputElement>(null);
  const [calibrating, setCalibrating] = useState(false);
  const thumb = useThumbnail(image.token, image.fileName);
  const local = pending.get(image.token);
  const modalities = tree.state === "ready" ? tree.tree.facets.get("modality")?.values ?? [] : [];
  const modalityName = (id: string) => {
    const v = modalities.find((m) => m.id === id);
    return v ? localised(v.name, lang) : id;
  };
  const priv = draft.specimen.geoprivacy === "private";
  const photo = image.photo;
  const noPlace = !draft.specimen.lat.trim() && !draft.specimen.lon.trim();
  const needsFile = image.source === "file" && !local && !hasFile;
  const title = image.source === "iiif" ? t("images.iiif") : image.fileName ?? t("images.noFile");

  return (
    <li className={styles.imageCard} data-family={image.family} data-needs-file={needsFile || undefined}>
      <div className={styles.imageHead}>
        <div className={styles.thumb} aria-hidden="true">
          {thumb ? <img src={thumb} alt="" style={photo?.orientation ? { imageOrientation: "from-image" } : undefined} />
            : <Glyph name={image.family === "macro" ? "camera" : "objective"} size={32} />}
        </div>
        <div className={styles.imageTitle}>
          <p className={styles.imageName}>
            <span className={styles.familyBadge}>{t(`family.${image.family}`)}</span>
            <span className={styles.fileName}>{title}</span>
          </p>
          <p className={styles.imageMeta}>
            {image.fileSize ? <span>{bytes(image.fileSize, lang)}</span> : null}
            {hasFile && !local ? <span className={styles.okText}>{t("images.fileKept")}</span> : null}
            {needsFile ? <span className={styles.warnText}>{t("images.needsFile")}</span> : null}
          </p>
        </div>
        <div className={styles.imageTools}>
          <IconButton icon="chevron-down" label={t("images.moveUp")} className={styles.up} disabled={index === 0}
            onClick={() => onMove(-1)} />
          <IconButton icon="chevron-down" label={t("images.moveDown")} disabled={index === count - 1}
            onClick={() => onMove(1)} />
          <IconButton icon="delete" label={t("images.remove", { name: title })} onClick={onRemove} />
        </div>
      </div>

      {image.source === "file" ? (
        <div className={styles.fileRow}>
          <Button size="small" variant="quiet" icon="upload" onClick={() => fileInput.current?.click()}>
            {local || hasFile ? t("images.replaceFile") : t("images.chooseFile")}
          </Button>
          <input ref={fileInput} type="file" hidden onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onReplaceFile(file);
            e.target.value = "";
          }} />
          {errorFor(`${at}.upload_id`) ? <p className={styles.fieldError}>{errorFor(`${at}.upload_id`)}</p> : null}
        </div>
      ) : (
        <TextField label={t("images.iiifUrl")} value={image.remoteIiif} type="url" inputMode="url"
          hint={t("images.iiifUrl.hint")}
          error={errorFor(`${at}.remote_iiif`) ?? errorFor(`${at}.upload_id`)}
          onChange={(e) => onChange({ remoteIiif: e.target.value })} />
      )}

      {photo && (photo.taken || photo.gps) ? (
        <div className={styles.photoFacts}>
          {photo.taken ? <p><Glyph name="clock" size={16} /><span>{t("images.taken", {
            when: date(photo.taken, { dateStyle: "medium", timeStyle: "short" }) })}</span></p> : null}
          {photo.gps ? (
            <p data-private={priv || undefined}>
              <Glyph name={priv ? "lock" : "pin"} size={16} />
              <span>{t("images.position", { lat: photo.gps.lat.toFixed(5), lon: photo.gps.lon.toFixed(5) })}</span>
              {priv ? <strong>{t("images.positionRemoved")}</strong> : null}
              {!priv && noPlace ? (
                <Button size="small" variant="quiet" icon="pin"
                  onClick={() => onUsePosition(photo.gps!.lat, photo.gps!.lon)}>{t("images.usePosition")}</Button>
              ) : null}
            </p>
          ) : null}
          {flagFor(`${at}.exif`, { prefix: true }) ? <p className={styles.flagText}>{flagFor(`${at}.exif`,
            { prefix: true })}</p> : null}
        </div>
      ) : null}

      <div className={styles.grid2}>
        <Select label={t("images.role")} value={image.role} error={errorFor(`${at}.role`)}
          onChange={(e) => onChange({ role: e.target.value as ImageDraft["role"] })}
          options={ROLES_BY_FAMILY[image.family].map((r) => ({ value: r, label: t(`role.${r}`) }))} />
        <Select label={t("images.licence")} value={image.licence} error={errorFor(`${at}.licence`)}
          hint={t("images.licence.hint")}
          onChange={(e) => onChange({ licence: e.target.value })}
          options={LICENCES.map((l) => ({ value: l.uri, label: l.short }))} />
        <TextField label={t("images.creator")} value={image.creator} maxLength={200}
          error={errorFor(`${at}.creator`)} onChange={(e) => onChange({ creator: e.target.value })} />
        <TextField label={t("images.rightsHolder")} optional value={image.rightsHolder} maxLength={200}
          hint={t("images.rightsHolder.hint")} error={errorFor(`${at}.rights_holder`)}
          onChange={(e) => onChange({ rightsHolder: e.target.value })} />
      </div>

      {image.family === "micro" ? (
        <div className={styles.microFields}>
          <div className={styles.grid2}>
            <Select label={t("images.modality")} value={image.modality} error={errorFor(`${at}.modality`)}
              onChange={(e) => onChange({ modality: e.target.value as ImageDraft["modality"] })}
              options={[{ value: "", label: t("images.modality.choose") },
                ...MODALITIES.map((m) => ({ value: m, label: modalityName(m) }))]} />
            <div className={styles.pixelField}>
              <TextField label={t("images.pixelSize")} optional value={image.pixelSize} inputMode="decimal"
                hint={image.calibration ? t("images.calibrated", { ...written(image.calibration),
                  pixels: Math.round(image.calibration.pixels), length: image.calibration.length })
                  : image.role === "pyramid" && image.source === "file" ? t("images.pixelSize.scanner")
                    : t("images.pixelSize.hint")}
                error={errorFor(`${at}.pixel_size_um`)}
                onChange={(e) => onChange({ pixelSize: e.target.value, calibration: null })} />
              <Button size="small" icon="ruler" onClick={() => setCalibrating(true)}>{t("calibrate.open")}</Button>
              {flagFor(`${at}.pixel_size_um`) ? <p className={styles.flagText}>{flagFor(`${at}.pixel_size_um`)}</p>
                : null}
            </div>
          </div>
          {image.role === "z_plane" ? (
            <div className={styles.grid3}>
              <TextField label={t("images.planeStack")} value={image.planeStack} maxLength={64}
                hint={t("images.planeStack.hint")} error={errorFor(`${at}.plane.stack`) ?? errorFor(`${at}.plane`)}
                onChange={(e) => onChange({ planeStack: e.target.value })} />
              <TextField label={t("images.planeIndex")} value={image.planeIndex} inputMode="numeric"
                error={errorFor(`${at}.plane.index`)} onChange={(e) => onChange({ planeIndex: e.target.value })} />
              <TextField label={t("images.planeDepth")} value={image.planeDepth} inputMode="decimal"
                hint={t("images.planeDepth.hint")} error={errorFor(`${at}.plane.depth_um`)}
                onChange={(e) => onChange({ planeDepth: e.target.value })} />
            </div>
          ) : null}
          {image.role === "polarised" ? (
            <div className={styles.grid2}>
              <fieldset className={styles.inlineChoice}>
                <legend className={styles.fieldLabel}>{t("images.polars")}</legend>
                {(["ppl", "xpl"] as const).map((state) => (
                  <label key={state}>
                    <input type="radio" name={`pol-${image.token}`} checked={image.polarisation === state}
                      onChange={() => onChange({ polarisation: state,
                        modality: state === "ppl" ? "polarised_ppl" : "polarised_xpl" })} />
                    <span>{modalityName(state === "ppl" ? "polarised_ppl" : "polarised_xpl")}</span>
                  </label>
                ))}
                {errorFor(`${at}.polarisation`, { prefix: true }) ? (
                  <p className={styles.fieldError}>{errorFor(`${at}.polarisation`, { prefix: true })}</p>) : null}
              </fieldset>
              <TextField label={t("images.polarAngle")} value={image.polarisationAngle} inputMode="decimal"
                hint={t("images.polarAngle.hint")} error={errorFor(`${at}.polarisation.angle_deg`)}
                onChange={(e) => onChange({ polarisationAngle: e.target.value })} />
            </div>
          ) : null}
        </div>
      ) : null}

      <TextField label={t("images.caption")} optional value={image.caption} maxLength={300}
        error={errorFor(`${at}.caption`)} onChange={(e) => onChange({ caption: e.target.value })} />

      {calibrating ? (
        <Calibrator onClose={() => setCalibrating(false)} onUse={(c) => {
          onChange({ pixelSize: written(c).value, calibration: c });
          setCalibrating(false);
        }} />
      ) : null}
    </li>
  );
}
