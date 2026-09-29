// An icon in the colour of the surrounding text: from the collection tree's sprite (U7, public/icons.svg) or from the
// interface glyphs (public/glyphs.svg: close, search, the rooms, language). With a label it is an image for assistive
// technology; without one it is decoration beside its own text.
import type { CSSProperties } from "react";

export type IconSize = 16 | 20 | 24 | 32 | 48;

export interface IconProps {
  /** The symbol id: a tree node ("life.plants") or a facet ("facet.modality.brightfield"). */
  name: string;
  size?: IconSize;
  /** A text alternative, when the icon carries meaning on its own. */
  label?: string;
  /** "tree" for collection and facet icons, "glyph" for interface actions. */
  set?: "tree" | "glyph";
  className?: string;
  style?: CSSProperties;
}

export function Icon({ name, size = 24, label, set = "tree", className, style }: IconProps) {
  const a11y = label ? { role: "img", "aria-label": label } : { "aria-hidden": true as const, focusable: false as const };
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" className={className} style={{ flex: "none", ...style }}
      {...a11y}>
      <use href={`/${set === "glyph" ? "glyphs" : "icons"}.svg#${name}`} />
    </svg>
  );
}

export function Glyph(props: Omit<IconProps, "set">) {
  return <Icon {...props} set="glyph" />;
}
