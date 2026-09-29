# 16 · The cabinet and label sheets

![The profile cabinet and the label sheets: an account's handle, made from its display name, addresses its profile, which never carries the email; the cabinet lays its published slides in one drawer per collection and lists its identifications with whether the community agrees now; the owner alone exports its slides with their exact places; selected slides print on a stock, a record of page, label size, grid, margins and pitches with its source, from a chosen position and a printer offset, each label fitted to its cell with the QR's quiet zone clear of text](svg/cabinet.svg)

A slide collection lives in drawers and is labelled by hand. U14 gives each contributor a place that shows what they
brought to the collection and how the community reads their work, and gives anyone a way to print a sheet of labels
for the slides they hold, on the label stock they have or on plain paper. The research is dossier 16 of the planning
record (fourteen label stocks, nine with full print layouts from their makers' datasheets, templates and die
drawings; plain paper with cut marks; iNaturalist's profile and export read from its source); the requirements are
R-1401 to R-1408 ([U14 requirements](../design/features/u14-cabinet/requirements.md)); the decisions are in the
[U14 design](../design/features/u14-cabinet/design.md).

## 1. A handle, never an email (R-1401)

An account has a display name and an email; a profile needs an address that shows neither. The handle is the display
name's letters and digits, accents removed, lower case, joined by hyphens, at most 60 characters; a number is added
when it is taken (`app/accounts/handles.py`):

| Display name | Handle |
|---|---|
| Ana Pérez | `ana-perez` |
| Ana Pérez (a second account) | `ana-perez-2` |
| María José Ñúñez-Oyarzún | `maria-jose-nunez-oyarzun` |
| `!!!` | `account` |

Registration makes it; migration 0012 made it for the accounts that existed, with the same rule written again (a
migration never imports the application's code). The profile's answer carries the handle, the display name, the role
and dates, as iNaturalist's `User.default_json_options` carries only the login, name, creation date and counts; the
email is never read by the profile's code. A slide names its contributor, and each identification its account, by
handle and display name, so both link to a cabinet.

## 2. What the profile counts (R-1402)

| Field | What it counts |
|---|---|
| `slides` | the account's contributions with the status `published` (a hidden slide has the status `hidden`, so it counts nowhere) |
| `by_collection` | the same, by collection (`life.insects`, the first two parts of the placement node) |
| `verified` | those whose badge is verified (U13) |
| `identifications` | its current, visible identifications of other accounts' published slides |
| `categories` | the same, by category: leading, improving, supporting, maverick (dossier 15) |
| `annotations` | its visible annotations on published slides |
| `joined`, `last_active` | the account's creation, and its newest published slide or identification |

iNaturalist computes "Last active" the same way when it has no stored value (from the newest observation or
identification). The contributor's first identification of their own slide is not an identification "of others'",
so a contributor's count starts at zero.

## 3. The cabinet (R-1403)

`/people/<handle>` shows the profile and two tabs. **Slides**: one drawer per collection, in the tree's order, each a
tray as a drawer lays it (the slide at its format's proportion, one scale for the tray, label end first), a page of
48 at a time. **Identifications**: newest first, each with its slide, the anchor it gave, its category, and whether
it names the slide's community anchor now (the last node of its lineage equals the slide's community node). The tab is
in the address (`?tab=identifications`), so a cabinet can be shared at either.

## 4. One's own export (R-1407)

`GET /api/people/me/slides.csv` answers only the signed-in account, with every slide of its own in any status (draft,
submitted, published, hidden), one row each, and the exact latitude and longitude even of an obscured or private
slide; it is never cached. Every public answer applies geoprivacy first (U7): an obscured slide is a point in its
0.2 degree cell, a private one has no point. iNaturalist leaves its `private_` columns empty unless
`coordinates_viewable_by?(user)`; Laminario has no trust between accounts, so only the owner's own export carries them.

The columns: `id, status, badge, catalogue_number, anchor_kind, anchor_ref, anchor_name, anchor_rank, community_node,
placement_node, format, preparation, stain, mountant, prepared_on, preparer, collected_on, collector, locality_text,
country, latitude, longitude, uncertainty_m, geoprivacy, permalink, created_at, published_at`.

## 5. A stock is data (R-1404)

Each stock in `app/labels/stocks.yaml` is a record: page (A4 or US Letter), label width and height, columns and rows,
the top and left margin to the first label's edge, the horizontal and vertical pitch, the corner radius, where the
numbers come from, and its warnings.

| Stock | Page | Label (mm) | Grid | Per page | Source |
|---|---|---|---|---|---|
| `a4-plain` | A4 | 20 x 26 | 8 x 9 | 72 | Laminario (dossier 16, section 2.2) |
| `letter-plain` | US Letter | 26 x 20 (on their side) | 7 x 11 | 77 | Laminario (dossier 16, section 2.2) |
| `divbio-misl-1000` | US Letter | 22.225 x 22.225 | 8 x 12 | 96 | Diversified Biotech's datasheet |
| `labtag-cla-4wh` | US Letter | 23.9 x 19.6 | 6 x 13 | 78 | LabTAG's template |
| `a4-25-66` | A4 | 25.4 x 25.4 | 6 x 11 | 66 | HERMA's die drawing (8831, 10107; LabTAG A4CL-112 shares it) |

The plain-paper grids fit $n$ labels of size $s$ with gutter $g$ in an available length $A$ (the page less 10 mm
margins):

$$n s + (n - 1) g \le A \quad\Longrightarrow\quad n = \left\lfloor \frac{A + g}{s + g} \right\rfloor .$$

On A4 (190 x 277 mm available), 20 x 26 mm labels with 2 mm gutters give $\lfloor 192/22 \rfloor = 8$ columns and
$\lfloor 279/28 \rfloor = 9$ rows, 72 labels; on US Letter (195.9 x 259.4 mm), on their side, $\lfloor 197.9/28
\rfloor = 7$ by $\lfloor 261.4/22 \rfloor = 11$, 77 (upright gives only 72: a ninth column needs 196.0 mm). The
grid is centred on the page, with a dashed cut line around each label, in the gutters.

The positions (`positions(stock, count, start, offset)`) go row by row from the chosen start (0-based) on the first
page, then from the first position of each following page, each moved by the printer offset $(d_x, d_y)$. A stock
whose template rows are closer than the label's nominal height (LabTAG CLA-4WH: a 19.49 mm pitch for a 19.6 mm label)
is drawn within the smaller of the two, so no two labels overlap. The test proves every label of every stock lies on
the page and apart from the others.

The warnings, worded in the print dialog:

| Warning | Why |
|---|---|
| `plain_paper` | cut along the marks and fix each label on the label end |
| `laser_xylene` | LabTAG's own test of its laser material: xylene "instantly" erases the printout (printout quality 1 of 5); label after mounting |
| `longer_than_label_end` | the label end is 20 mm long; a 22.2 mm square reaches 2.2 mm past it, a 25.4 mm one 5.4 mm |
| `wider_than_us_slide` | a 25.4 mm label is 0.4 mm wider than a 25 mm US slide |

## 6. One label, any cell (R-1405)

The label is U11's frosted-end label (the collection's hue band, the catalogue number in bold, the name with its
epithets in italic, the data lines, the QR) fitted to the stock's cell, less 0.8 mm on every side (`app/labels/cell.py`).
The QR goes at the cell's foot or on its right, at 14 mm with its four-module quiet zone, shrinking in 0.5 mm steps to
no less than 11 mm (29 modules of 0.3 mm). Every arrangement and size is tried, and the label keeps the one that, in
this order:

1. sets the catalogue number and the name complete (no line cut short);
2. in the fewest lines (a word split across lines is a line more);
3. sets the most data lines;
4. has the largest QR.

No text enters the quiet zone. On stock nothing is drawn outside the labels, and no outline (it would print on the
label); on plain paper a dashed cut line runs around each label, in the gutters, and the page says so at its foot,
in the sheet's language.

## 7. The sheet and the test page (R-1406)

`GET /api/labels/sheet.pdf?stock=&slides=&start=&dx=&dy=&lang=` draws the labels of up to 500 published slides with
reportlab at 1:1; `test=true` draws the stock's test page instead: every label's outline, the stock's name and the
instruction to print at 100 % on plain paper and hold the page against a sheet of labels, as Diversified Biotech's
instructions ask. The test proves each outline measures the stock's label size and lies at its position within
0.1 mm. Anyone may print a published slide's labels, as anyone opens its single label (U11).

The print dialog of the cabinet chooses the stock (grouped as plain paper or label sheets, with its measurements,
source and warnings), the start position on a map of the sheet (a radio group, one position per label, the labels to
be printed shaded), and the printer offset in 0.1 mm steps up to 10 mm either way. The last stock and each stock's
offset are kept in the browser's storage on the device: the offset belongs to the printer, not to the account.

## 8. Gates and tests

| Gate | Checks |
|---|---|
| `tests/people/test_profile.py` | handles made plain and unique; the profile's counts, without the email, and a hidden slide leaving them; the cabinet's slides by collection and pages, the identifications with the community flag; the slide and identifications naming accounts by handle (R-1401 to R-1403) |
| `tests/people/test_export.py` | one's own slides, any status, with an obscured slide's exact place; no export without signing in, none of another's (R-1407) |
| `tests/people/test_sheets.py` | the stocks over HTTP; a sheet, a test page, and every refusal (unknown stock or slide, no slides, a start past the sheet, an offset past 10 mm, more than 500 slides) |
| `tests/labels/test_sheet.py` | every stock places its labels on the page and apart (R-1404); each label's content inside its cell, the quiet zone clear (R-1405); the test page's outlines at their size and position within 0.1 mm (R-1406) |
| `frontend/src/labels/printing.test.ts` | the offset bounded and kept per stock; the pages a sheet fills; the sheet's address |
| `frontend/gates/cabinet.mjs` | in its own sandbox: two slides published through tusd; a visitor follows a slide's contributor to their cabinet, selects both slides, prints them on a stock from position 5 with an offset, prints the test page, and finds the offset kept for that stock; the identifier's cabinet from the slide's identifications; the owner's export from the account menu; the cabinet, its identifications and the print dialog at every width, room and language; nothing moving with reduced motion (R-1408, R-080, R-085) |
