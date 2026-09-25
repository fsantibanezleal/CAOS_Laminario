// The web app mounts here. The interface arrives with U9 (design system) and U10 onward; until then this
// entry exists so the type check and the build have a root, and it renders the product name.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import type { SlideRecord } from "./contract/catalog";

export type { SlideRecord };

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(
    <StrictMode>
      <main>Laminario</main>
    </StrictMode>,
  );
}
