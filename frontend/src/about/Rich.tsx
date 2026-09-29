// Draws the About content's blocks: paragraphs, headings, lists, equations (KaTeX), code, figures. Live blocks are
// drawn by the place, which holds the numbers.
import katex from "katex";
import "katex/dist/katex.min.css";
import { Fragment, type ReactNode } from "react";
import type { AboutContent, Block, Inline } from "./model";
import { Figure } from "./figures";
import styles from "./About.module.css";

export function Tex({ tex, display = false }: { tex: string; display?: boolean }) {
  // The source is this page's own content (content.en.ts, content.es.ts), never a visitor's text.
  const html = katex.renderToString(tex, { displayMode: display, throwOnError: false, output: "htmlAndMathml" });
  return display
    ? <div className={styles.math} dangerouslySetInnerHTML={{ __html: html }} />
    : <span dangerouslySetInnerHTML={{ __html: html }} />;
}

export function Inlines({ parts }: { parts: Inline[] }) {
  return (
    <>
      {parts.map((part, i) => {
        if (typeof part === "string") return <Fragment key={i}>{part}</Fragment>;
        if ("em" in part) return <em key={i}>{part.em}</em>;
        if ("strong" in part) return <strong key={i}>{part.strong}</strong>;
        if ("a" in part) return <a key={i} href={part.href} rel="noreferrer">{part.a}</a>;
        if ("m" in part) return <Tex key={i} tex={part.m} />;
        return <code key={i}>{part.code}</code>;
      })}
    </>
  );
}

export function BlockView({ block, content, live }: { block: Block; content: AboutContent;
  live: (what: Extract<Block, { kind: "live" }>["what"]) => ReactNode }) {
  switch (block.kind) {
    case "p": return <p><Inlines parts={block.text} /></p>;
    case "h3": return <h3 className={styles.h3}>{block.text}</h3>;
    case "list": return <ul className={styles.list}>{block.items.map((item, i) => <li key={i}><Inlines parts={item} /></li>)}</ul>;
    case "math": return <Tex tex={block.tex} display />;
    case "code": return <pre className={styles.code}><code>{block.text}</code></pre>;
    case "figure": return (
      <figure className={styles.figure} data-figure={block.figure}>
        <Figure id={block.figure} labels={content.figures[block.figure]} />
        <figcaption><Inlines parts={block.caption} /></figcaption>
      </figure>
    );
    case "live": return <>{live(block.what)}</>;
  }
}
