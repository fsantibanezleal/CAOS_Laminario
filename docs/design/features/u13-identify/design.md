# U13 · Identify · design

The research is dossier 15 of the planning record (iNaturalist's community taxon and quality grade read from its
source, moderation, every anchor as a lineage, the twelve scenarios). How the parts fit is the wiki page
[15 Identify](../../../architecture/15_identify.md). This page records the unit's decisions.

## What the unit delivers

| Part | Where |
|---|---|
| Identifications, votes, flags and moderation actions; the backfilled first identifications | migration 0011, `app/db/models.py` |
| Every anchor as a lineage of node ids | `app/community/lineage.py` |
| The agreement rule, a pure function over current identifications | `app/community/agreement.py` |
| The badge from the slide checks and the community | `app/community/quality.py`, `app/services/catalog.py` |
| Adding, withdrawing and restoring identifications; the vote; the slide following the community | `app/services/community.py`, `app/routers/community.py` |
| Flags, hiding and restoring, the audit | `app/services/moderation.py`, `app/routers/moderation.py` |
| The Identify place, identifications on the slide place, the moderation place | `frontend/src/places/identify/`, `frontend/src/community/`, `frontend/src/places/moderate/` |
| The browser gate | `frontend/gates/identify.mjs` |

## Decisions

- **One rule for every kind.** An anchor becomes a lineage: a root per kind (`taxon`, `mineral`, `rock`, `crystal`,
  `material`), then the kind's own hierarchy (the GBIF backbone keys from the kingdom, the Nickel-Strunz path, the
  rock or material family path, the crystal origin then category then system), then the anchor. iNaturalist's rule
  (dossier 15, section 2) runs on node ids: the cumulative count, the disagreements outside the branch, the explicit
  disagreements with a finer anchor, a score strictly above two thirds with at least two identifications, the deepest
  qualifying node. A root is never a community anchor. The lineage is stored with the identification, as it was when
  it was made, so the rule never needs the network.
- **Identifications belong to accounts with the identify capability** (identifier and above, R-052), on published
  slides; each account has one current identification per slide; a new one supersedes it; withdrawing leaves none
  current; restoring makes a chosen earlier one current again. A comment of up to 1,000 characters goes with it.
  Naming an ancestor of the slide's anchor asks whether the identifier disagrees with the finer anchor (R-1302);
  naming anything outside the slide's branch is a disagreement by itself.
- **The first identification is the slide's own (R-1309).** A contribution's anchor is its contributor's
  identification, made when the slide is published; a base slide's determination is the source's, with no account
  (dossier 15, section 5; the SDD's non-goal 6: recorded as the museum's determination, not verified by Laminario).
  Migration 0011 creates them for the slides published before it.
- **The slide follows the community (R-1303).** When the community node is an anchor Laminario can name (a taxon at any
  rank, a mineral species or group, a crystal origin, category or system, a rock or a material), the slide's anchor
  becomes it and the tree places the slide again, keeping its drawer when the drawer still accepts it and a curator's
  override. A node that is not an anchor (a rock family, a Nickel-Strunz class) is shown as what the community agrees
  on while the slide keeps its anchor. A taxon's name and rank at an ancestor come from the taxon cache, or GBIF once.
- **The badge (R-1304)** keeps the computed checks (M9) and adds the community: verified at the depth the kind needs
  (a taxon at species or below; a mineral species; a rock; a crystal's system or category; a material), or, voted as
  good as it can be, at the coarser depth it allows (a taxon below family; a mineral group; a crystal origin); a
  vote that leaves an anchor coarser than that makes it reference. Identifiers vote once each; more votes for "as good
  as it can be" than for "needs more" decide; a change of the community anchor clears the votes.
- **Moderation (R-1305, R-1306)** mirrors iNaturalist's: any signed-in account flags a slide, an identification or an
  annotation (spam, inappropriate, copyright, a wrong record, other); curators resolve flags with a comment; curators
  hide and restore with a reason of 10 to 2,000 characters, and only the curator who hid an item, or an admin, restores
  it; every action is kept. A hidden slide has the `hidden` status and leaves every public listing, count, search,
  map, manifest and tile; its contributor sees the reason with the case. A hidden identification leaves the agreement,
  and a hidden annotation is not served.
- **The places.** `/identify` is the queue: published slides whose badge is needs ID, filtered by collection and kind,
  optionally without those the account identified, oldest first so none waits forever. The slide place shows the
  community anchor with how it was reached, every identification with its category (leading, improving, supporting,
  maverick) and the form to add one; `/moderate` is the curators' flags and hidden items.
