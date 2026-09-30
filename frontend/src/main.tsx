import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import type { SlideRecord } from "./contract/catalog";
import "./design/fonts.css";
import "./design/tokens.css";
import "./design/base.css";
import "./glass/surface.css";

export type { SlideRecord };

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
