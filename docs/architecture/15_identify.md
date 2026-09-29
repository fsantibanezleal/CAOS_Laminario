# 15 · Identify

![Identification and moderation: every anchor becomes a lineage of node ids; identifications (the contributor's or the source's first, then identifiers', one current per account) feed the agreement rule, whose deepest node with at least two identifications and a score above two thirds is the community anchor; the slide follows it and the tree places it again; the badge adds the slide checks and the vote on whether the name can still be improved; curators resolve flags and hide or restore with a reason](svg/identify.svg)

Identification is how a collection of contributed slides becomes trustworthy without a curator checking each one:
people who know the organisms, rocks and minerals say what a slide shows, and the name the most of them agree on is
the slide's. The rule is iNaturalist's community taxon, read from its source; Laminario applies it to every kind of
anchor. The research is dossier 15 of the planning record; the requirements are R-088 and R-1301 to R-1309
([U13 requirements](../design/features/u13-identify/requirements.md)); the decisions are in the
[U13 design](../design/features/u13-identify/design.md).

## 1. Every anchor as a lineage

The rule needs a hierarchy, so each anchor becomes a lineage: node ids from its kind's root down to the anchor
(`app/community/lineage.py`).

| Kind | Lineage | Example |
|---|---|---|
| taxon | the GBIF backbone keys from the kingdom down, then the accepted taxon | `taxon`, `taxon:1`, `taxon:54`, ..., `taxon:1032608` |
| mineral | the Nickel-Strunz path, then the species; a group stops at its code | `mineral:9`, `mineral:9.A`, `mineral:9.A.C`, `mineral:9.A.C.05`, `mineral:9.A.C.05/forsterite` |
| rock | the family path, then the rock | `rock:igneous`, `rock:igneous.exotic`, `rock:igneous.exotic/carbonatite` |
| crystal | the origin, then the snow category, then the system | `crystal:ice`, `crystal:ice.P`, `crystal:ice.P/hexagonal` |
| material | the family, then the material | `material:fibre`, `material:fibre/cotton` |

The kinds share no node, so a rock against a mineral is a disagreement. An identification keeps its lineage as it was
when it was made (and the slide's anchor of the time), so the rule never reads the network.

## 2. The agreement rule (R-088, R-1302)

Only current, visible identifications count, one per account (a new one supersedes the account's earlier one). With
fewer than two, there is no community anchor. For every node $t$ named by an identification or on the lineage of one:

- $c(t)$, the **cumulative count**: identifications of $t$ or of a node below it;
- $d(t)$, the **disagreement count**: identifications of a node that is neither $t$'s ancestor nor below $t$;
- $a(t)$, the **ancestor disagreements**: identifications of an ancestor $A$ of the slide's anchor $P$ of the time,
  made as an explicit disagreement with it, which disagree with every node from $A$'s child on $P$'s lineage down to
  $P$ (counted while some current identification still names $P$ or a node below it);

$$\mathrm{score}(t) = \frac{c(t)}{c(t) + d(t) + a(t)}.$$

The community anchor is the deepest node with $c(t) > 1$ and $\mathrm{score}(t) > 2/3$, strictly, never a kind's root.
The qualifying nodes lie on one chain (two siblings cannot both hold more than two thirds), so the deepest is the
finest. An identification of an ancestor that does not disagree counts for the ancestor and against nothing: the
interface asks the identifier which it is whenever the name they chose is broader than the slide's (R-1302).

Each identification is shown with its category: **leading** (below the community anchor, or none yet), **improving**
(the first at or above it on its branch), **supporting** (agreeing after), **maverick** (outside its branch).

The gate is a table of scenarios computed by hand in the dossier; S1 and S2 are species of genus G:

| Identifications | Community anchor | Why |
|---|---|---|
| S1, S1 | S1 | $c = 2$, score 1 |
| S1, S2 | G | S1 and S2 have $c = 1$; G has $c = 2$, score 1 |
| S1, S1, S1, S2 | S1 | $3/4 > 2/3$ |
| S1, S1, S2 | G | S1 scores exactly $2/3$, not more |
| S1, S1, G (disagreeing with S1) | G | S1 scores $2 / (2 + 0 + 1) = 2/3$ |
| S1, S1, G (not disagreeing) | S1 | the coarser identification counts for G only |
| granite, granodiorite | their family | the vocabulary's lineage, as a taxon's |
| quartz (a mineral), quartzite (a rock) | none | no shared node |

## 3. The first identification and the slide following the community (R-1309, R-1303)

A contribution's anchor is its contributor's identification, made when the slide is published; a base slide's
determination is the source's, with no account. Laminario records the museum's determination as such and does not
verify it (the SDD's non-goal 6); the community may. A re-import that changes a base slide's determination records it
as the source's new identification. `python -m app.community backfill` gives every slide published before U13 its
first identification and its badge, idempotently.

When the community anchor is one Laminario can name (a taxon at any rank, a mineral species or group, a crystal's
origin, category or system, a rock, a material), the slide's anchor becomes it, and the tree places the slide again:
it keeps its drawer when the drawer still accepts the new anchor, and a curator's override always. A node that is not
an anchor (a rock family, a Nickel-Strunz class) is shown as what the community agrees on while the slide keeps its
anchor. A taxon above the ones named, not yet in the cache, is fetched from GBIF once, then read locally.

## 4. The badge (R-1304)

The slide checks of M9 (licence and provenance of every image, a pixel size for every micro image, the modality, a
macro and a micro image) and the community decide it, in iNaturalist's order:

| Badge | When |
|---|---|
| reference | a check fails; or the community voted "as good as it can be" and the anchor is coarser than its kind allows |
| needs ID | more identifiers say it still needs identification than say it is as good as it can be; or no community anchor; or an anchor coarser than its kind needs |
| verified | the community anchor is as fine as its kind needs (a taxon at species or below, a mineral species, a rock, a crystal's system or category, a material), or, voted as good as it can be, at the coarser depth its kind allows (a taxon below family, a mineral group, a crystal origin) |

A change of the community anchor clears the votes. The base collection's scans mostly have no pixel size and no
photograph of the slide, so almost all of it is reference by these checks: a slide without a scale cannot support a
measurement (dossier 05). The Identify place lists needs-ID slides by default and the reference ones on request.

## 5. Moderation (R-1305, R-1306)

Any signed-in account flags a slide, an identification or an annotation (a wrong record, copyright, inappropriate,
spam, something else) with a comment; the curators list the open flags and resolve each with a comment. A curator
hides an item with a reason of at least 10 characters, and only that curator or an admin restores it; every hiding and
restoring is kept (`moderation_action`). A hidden slide takes the `hidden` status, so every public listing, count,
search, facet, map point, manifest and tile leaves it (they all read published slides only), and its contributor sees
the reason with the case; a re-import never clears it. A hidden identification leaves the agreement and is shown only
to its author and the curators; a hidden annotation is not served.

## 6. The places

`/identify` is the queue: published slides whose badge is needs ID, as a tray, oldest first so none waits forever,
filtered by collection, kind and badge, and, for an identifier, without the slides they identified. The slide place's
Identifications section shows what the community agrees on, with the supporting count against the two thirds it had
to exceed, the badge and what it means, the vote, every identification with its category, and the form (the anchor
combobox of the contribute place; the question when the name is broader than the slide's). `/moderate` is the
curators': open and resolved flags, the items hidden now, and the log.

## 7. Gates and tests

| Gate | Checks |
|---|---|
| `tests/community/test_agreement.py` | the twelve scenarios of the dossier (R-088, R-1302), the formula in numbers, a withdrawn disagreement, the categories |
| `tests/community/test_identifications.py` | one current identification per account, withdraw and restore, the roles; the ancestor's question; the first identification of a contribution and of a base slide, and the backfill's idempotence (R-1301, R-1302, R-1309) |
| `tests/community/test_follow.py` | the slide taking the genus, then the species; a drawer that refuses the new anchor, and a curator's override kept (R-1303) |
| `tests/community/test_quality.py` | the badge rule over the kinds, the votes deciding and being cleared (R-1304) |
| `tests/community/test_moderation.py` | flags and their resolution; a hidden slide gone from every public place and back; hidden identifications and annotations (R-1305, R-1306) |
| `tests/community/test_queue.py` | the queue by badge, collection and kind, oldest first, without the account's own (R-1307) |
| `frontend/gates/identify.mjs` | in its own sandbox: a contributed slide published through tusd, two identifiers agreeing from the Identify place until it is verified, a curator hiding it (gone for a visitor, its contributor told why) and restoring it from the moderation place; the places at every width, room and language (R-1308, R-080) |
