// A name as the codes of nomenclature set it (slide/names.ts): the epithets of a genus or anything below it italic,
// a rank marker and the authorship roman; a family, a class, a rock or a mineral roman.
import { nameParts } from "../../slide/names";

export function AnchorName({ kind, rank, name }: { kind: string; rank?: string | null; name: string }) {
  const parts = nameParts({ kind: kind as "taxon", rank: rank ?? null, name });
  return (
    <>
      {parts.map((part, i) => (
        <span key={i}>{i ? " " : ""}{part.italic ? <i>{part.text}</i> : part.text}</span>
      ))}
    </>
  );
}
