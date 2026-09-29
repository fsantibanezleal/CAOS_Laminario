// What kind of navigation brought the visitor to the current place, and where each place was scrolled.
//
// A link (pushState) opens the new place at its top and moves the focus to its heading; the back and forward
// buttons (popstate) return to the scroll position the place had; a change of filters in the same place
// (replaceState) keeps both. wouter dispatches pushState and replaceState events from the history methods it wraps.

export type NavigationKind = "load" | "push" | "replace" | "pop";

let kind: NavigationKind = "load";
const positions = new Map<string, number>();
const key = () => `${location.pathname}${location.search}`;
let pending = false;

function record(): void {
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => {
    pending = false;
    positions.set(key(), window.scrollY);
  });
}

if (typeof window !== "undefined") {
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  addEventListener("scroll", record, { passive: true });
  addEventListener("popstate", () => { kind = "pop"; });
  addEventListener("pushState", () => { kind = "push"; });
  addEventListener("replaceState", () => { kind = "replace"; });
}

export function navigationKind(): NavigationKind {
  return kind;
}

/** Where the current address was scrolled when the visitor last left it, if they did. */
export function savedScroll(): number | undefined {
  return positions.get(key());
}
