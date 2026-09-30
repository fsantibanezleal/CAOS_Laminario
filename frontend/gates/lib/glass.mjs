// The gates' way through the glass interface (U17): a slide is reached as a visitor reaches it, with the pointer on the
// stage. The accessible layer writes where each slide lies on the stage; a slide out of view is brought round with the
// set's own Next button; a click chooses it and a click on the chosen slide opens it, through the scene's own hit test.
// Where the device draws flat, the flat glass slide is the link.

/** The ids a set holds, in order. */
export async function glassIds(page, set) {
  return page.$$eval(`[data-glass-set="${set}"] [data-glass-item]`, (all) => all.map((a) => a.dataset.glassItem));
}

/** The hrefs a set's slides open. */
export async function glassHrefs(page, set) {
  return page.$$eval(`[data-glass-set="${set}"] [data-glass-item]`, (all) => all.map((a) => a.getAttribute("href")));
}

/** Wait until the set's scene has placed its slides (or the set is drawn flat). */
export async function glassReady(page, set, timeout = 60_000) {
  await page.waitForFunction((name) => {
    const s = document.querySelector(`[data-glass-set="${name}"]`);
    return s && (s.getAttribute("data-drawn") === "flat" || s.querySelector("[data-glass-item][data-pick-x]"));
  }, set, { timeout });
}

async function spot(page, set, id) {
  return page.evaluate(([name, item]) => {
    const s = document.querySelector(`[data-glass-set="${name}"]`);
    const link = s?.querySelector(`[data-glass-item="${item}"]`);
    const stage = s?.querySelector("[data-glass-stage]")?.getBoundingClientRect();
    if (!link || !stage || !link.hasAttribute("data-pick-x")) return null;
    return { x: stage.left + Number(link.dataset.pickX), y: stage.top + Number(link.dataset.pickY),
      inside: Number(link.dataset.pickX) > 2 && Number(link.dataset.pickX) < stage.width - 2
        && Number(link.dataset.pickY) > 2 && Number(link.dataset.pickY) < stage.height - 2 };
  }, [set, id]);
}

/** Open slide ``id`` of set ``set`` by pointer: bring it into view, choose it, open it. Resolves when the address
 * changed. */
export async function openGlass(page, set, id, { timeout = 60_000 } = {}) {
  const start = page.url();
  const deadline = Date.now() + timeout;
  await glassReady(page, set, timeout);
  const drawn = await page.getAttribute(`[data-glass-set="${set}"]`, "data-drawn");
  if (drawn === "flat") {
    await page.locator(`[data-glass-set="${set}"] [data-glass-flat="${id}"]`).first().click();
    await page.waitForURL((url) => url.href !== start, { timeout });
    return;
  }
  const ids = await glassIds(page, set);
  const target = ids.indexOf(id);
  if (target < 0) throw new Error(`the set ${set} holds no ${id}`);
  await page.locator(`[data-glass-set="${set}"] [data-glass-stage]`).scrollIntoViewIfNeeded();
  let clicks = 0;
  while (Date.now() < deadline) {
    const here = await spot(page, set, id);
    if (!here || !here.inside) {
      // Out of view: turn the set toward it with its own buttons.
      const position = await page.textContent(`[data-glass-set="${set}"] [aria-live=polite]`);
      const current = Number((position ?? "").trim().split(/\s/)[0]) - 1;
      const name = current < target ? /next/i : /previous/i;
      await page.locator(`[data-glass-set="${set}"]`).getByRole("button", { name }).click();
      await page.waitForTimeout(900);
      continue;
    }
    await page.mouse.click(here.x, here.y);
    clicks += 1;
    const moved = await page.waitForURL((url) => url.href !== start, { timeout: 1_500 }).then(() => true, () => false);
    if (moved) return;
    if (clicks > 6) break;
    await page.waitForTimeout(700);
  }
  throw new Error(`could not open ${id} from the set ${set} by pointer`);
}
