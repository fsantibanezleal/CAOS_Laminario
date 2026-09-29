// The frame of every place: the masthead with the trail, the document title, and the place's heading, which takes
// the focus after a navigation (a screen reader announces where the visitor arrived) and is where the skip link
// lands. Opened by a link, the place starts at its top; opened by back or forward, it returns to its scroll position
// once its content is there (``ready``).
import { useEffect, useLayoutEffect, useRef, type ReactNode } from "react";
import { useLocation } from "wouter";
import { useI18n } from "../i18n";
import { Footer } from "../ui/Footer";
import { Masthead } from "../ui/Masthead";
import { PlaceTrail, type Place as TrailPlace } from "../ui/PlaceTrail";
import { navigationKind, savedScroll } from "./navigation";
import styles from "./Place.module.css";

export interface PlaceProps {
  /** The place's name, for the heading and the document title. */
  title: string;
  /** Drawn in the heading instead of the title text (an icon beside it, a subtitle), when given. */
  heading?: ReactNode;
  trail?: TrailPlace[];
  /** Whether the content the scroll position depends on has arrived. */
  ready?: boolean;
  wide?: boolean;
  children: ReactNode;
}

export function Place({ title, heading, trail, ready = true, wide = false, children }: PlaceProps) {
  const { t } = useI18n();
  const [location] = useLocation();
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    document.title = title === t("app.name") ? title : `${title} · ${t("app.name")}`;
  }, [title, t]);

  useLayoutEffect(() => {
    const kind = navigationKind();
    if (kind === "push") {
      window.scrollTo(0, 0);
      headingRef.current?.focus({ preventScroll: true });
    }
    // A pop keeps the focus where the browser leaves it; its scroll waits for the content (below).
  }, [location]);

  useEffect(() => {
    if (!ready || navigationKind() !== "pop") return;
    const y = savedScroll();
    if (y !== undefined) window.scrollTo(0, y);
  }, [ready, location]);

  return (
    <>
      <Masthead trail={trail && trail.length > 1 ? <PlaceTrail places={trail} /> : undefined} />
      <main id="content" className={[styles.main, wide ? styles.wide : ""].join(" ")}>
        <h1 ref={headingRef} tabIndex={-1} className={styles.heading}>{heading ?? title}</h1>
        {children}
      </main>
      <Footer />
    </>
  );
}
