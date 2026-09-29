// The third section: the slide's images. Macro images are photographs (the specimen, the place, the slide, its
// label); micro images are what the microscope saw: a field, a scanner's whole-slide file, a plane of a focal stack,
// a polarised view, or an image already served by a IIIF service. Files are chosen or dropped; each photograph's
// date and position are read at once (R-087) and shown, and in a private case the page says the position will be
// removed before the file leaves (R-1204). Nothing is sent from here: the files go once the case is stored.
import { useEffect, useRef, useState, type DragEvent } from "react";
import { newImage, type Family, type ImageDraft } from "../../contribute/draft";
import { pending } from "../../contribute/pending";
import { drawable, looksLikeScannerFile, readPhoto } from "../../contribute/photo";
import { useSession } from "../../account/session";
import { useI18n } from "../../i18n";
import { Button } from "../../ui/Button";
import { Glyph } from "../../ui/Icon";
import styles from "./Contribute.module.css";
import { ImageCard } from "./ImageCard";
import type { SectionProps } from "./sections";

const PHOTO_ACCEPT = "image/jpeg,image/png,image/webp,image/tiff,.jpg,.jpeg,.png,.webp,.tif,.tiff";
const MICRO_ACCEPT = `${PHOTO_ACCEPT},.svs,.ndpi,.mrxs,.scn,.vms,.vmu,.bif,.dcm,.zip,.isyntax`;

/** Which family and role a dropped file most likely is: a scanner file is a whole-slide micro image. */
export function guess(file: File): { family: Family; role: ImageDraft["role"] } {
  if (looksLikeScannerFile(file.name, file.size)) return { family: "micro", role: "pyramid" };
  return { family: "macro", role: "specimen" };
}

export function ImagesSection(props: SectionProps & { hasFile: (token: string) => boolean }) {
  const { draft, update, errorFor } = props;
  const { t } = useI18n();
  const session = useSession();
  const photoInput = useRef<HTMLInputElement>(null);
  const microInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const creator = session.account?.display_name ?? "";
  const images = draft.images;

  const setImage = (token: string, change: Partial<ImageDraft>) =>
    update((d) => ({ ...d, images: d.images.map((i) => (i.token === token ? { ...i, ...change } : i)) }));

  const read = async (token: string, file: File) => {
    const reading = await readPhoto(file);
    if (reading.kind === "other") return;
    setImage(token, { photo: { taken: reading.taken, orientation: reading.orientation, gps: reading.gps } });
  };

  const add = (files: File[], family?: Family) => {
    const added: ImageDraft[] = files.map((file) => {
      const g = guess(file);
      const f = family ?? g.family;
      const image = newImage(f, creator);
      image.role = f === g.family ? g.role : f === "micro" ? "single" : "specimen";
      image.fileName = file.name;
      image.fileSize = file.size;
      pending.set(image.token, file);
      return image;
    });
    update((d) => ({ ...d, images: [...d.images, ...added] }));
    added.forEach((image, i) => void read(image.token, files[i]));
  };

  const addIiif = () => {
    const image = newImage("micro", creator);
    image.source = "iiif";
    image.role = "pyramid";
    update((d) => ({ ...d, images: [...d.images, image] }));
  };

  const replaceFile = (token: string, file: File) => {
    pending.set(token, file);
    setImage(token, { fileName: file.name, fileSize: file.size, photo: null });
    void read(token, file);
  };

  const remove = (token: string) => {
    pending.delete(token);
    update((d) => ({ ...d, images: d.images.filter((i) => i.token !== token) }));
  };

  const move = (token: string, by: -1 | 1) => update((d) => {
    const list = [...d.images];
    const at = list.findIndex((i) => i.token === token);
    const to = at + by;
    if (at < 0 || to < 0 || to >= list.length) return d;
    [list[at], list[to]] = [list[to], list[at]];
    return { ...d, images: list };
  });

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length) add(files);
  };

  // A photograph's position, offered for the specimen's place when the place has none yet.
  const usePosition = (lat: number, lon: number) => update((d) => ({ ...d, specimen: { ...d.specimen,
    lat: lat.toFixed(6), lon: lon.toFixed(6), uncertainty: d.specimen.uncertainty || "30" } }));

  const macro = images.filter((i) => i.family === "macro").length;
  const micro = images.length - macro;

  return (
    <div className={styles.sectionBody}>
      <div className={styles.dropZone} data-dragging={dragging || undefined}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
        onDrop={onDrop}>
        <Glyph name="upload" size={32} />
        <p className={styles.dropTitle}>{t("images.drop")}</p>
        <p className={styles.fieldHint}>{t("images.drop.hint")}</p>
        <div className={styles.addRow}>
          <Button icon="camera" onClick={() => photoInput.current?.click()}>{t("images.addPhotos")}</Button>
          <Button icon="objective" onClick={() => microInput.current?.click()}>{t("images.addMicro")}</Button>
          <Button variant="quiet" icon="plus" onClick={addIiif}>{t("images.addIiif")}</Button>
        </div>
        <input ref={photoInput} type="file" multiple accept={PHOTO_ACCEPT} hidden
          onChange={(e) => { add(Array.from(e.target.files ?? []), "macro"); e.target.value = ""; }} />
        <input ref={microInput} type="file" multiple accept={MICRO_ACCEPT} hidden
          onChange={(e) => { add(Array.from(e.target.files ?? []), "micro"); e.target.value = ""; }} />
      </div>
      {errorFor("assets") ? <p className={styles.fieldError} role="alert">{errorFor("assets")}</p> : null}

      {images.length ? (
        <p className={styles.countLine}>{t("images.count", { macro, micro })}</p>
      ) : (
        <p className={styles.fieldHint}>{t("images.none")}</p>
      )}

      <ol className={styles.imageList}>
        {images.map((image, index) => (
          <ImageCard key={image.token} image={image} index={index} count={images.length} draft={draft}
            onChange={(change) => setImage(image.token, change)} onRemove={() => remove(image.token)}
            onMove={(by) => move(image.token, by)} onReplaceFile={(file) => replaceFile(image.token, file)}
            onUsePosition={usePosition} hasFile={props.hasFile(image.token)} errorFor={errorFor}
            flagFor={props.flagFor} />
        ))}
      </ol>
    </div>
  );
}

/** A thumbnail of a chosen file the browser can draw, released when the card goes. */
export function useThumbnail(token: string, name: string | null): string | null {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    const file = pending.get(token);
    if (!file || !drawable(file)) {
      setUrl(null);
      return undefined;
    }
    const made = URL.createObjectURL(file);
    setUrl(made);
    return () => URL.revokeObjectURL(made);
  }, [token, name]);
  return url;
}

