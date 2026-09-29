# U14 · The profile cabinet and printable label sheets · design

The research is dossier 16 of the planning record (fourteen label stocks, nine with full print layouts from their
makers' datasheets, templates and die drawings; plain paper with cut marks; iNaturalist's profile and export read from
its source). How the parts fit is the wiki page [16 Cabinet and labels](../../../architecture/16_cabinet.md).

## What the unit delivers

| Part | Where |
|---|---|
| A public handle per account (migration 0012), made from the display name, unique | `app/accounts/handles.py`, `app/db/models.py` |
| The profile and its cabinet: counts, slides by collection, identifications with their category | `app/services/people.py`, `app/routers/people.py` |
| The export of one's own slides as CSV | `app/services/people.py` |
| Label stocks as data, and the sheet renderer (labels fitted to each stock's cell; the test page) | `app/labels/stocks.yaml`, `app/labels/stocks.py`, `app/labels/cell.py`, `app/labels/sheet.py` |
| The cabinet place, the print dialog, the account menu's cabinet and the slide's contributor link | `frontend/src/places/people/`, `frontend/src/labels/` |
| The browser gate | `frontend/gates/cabinet.mjs` |

## Decisions

- **A handle, never an email (R-1401).** Laminario's accounts have a display name and an email; the profile needs an
  address that shows neither. The handle is the display name's letters and digits, lower case, joined by hyphens
  (accents removed), with a number when taken (`ana-perez`, `ana-perez-2`); it is made at registration and, for the
  accounts made before, by migration 0012. The profile's JSON carries the handle, the display name, the role and the
  dates; the email is never in a profile's page or answer (iNaturalist's `default_json_options`, dossier 16 section
  3.2).
- **What the profile counts (R-1402).** Published slides, in total and by collection; verified slides; identifications
  for others by category (leading, improving, supporting, maverick, dossier 15); when the account joined and was last
  active (its newest slide or identification). Hidden slides and identifications count nowhere.
- **The cabinet (R-1403)** is the account's slides laid out as drawers: one tray per collection, the slides at their
  format's proportion (the explore tray); and its identifications, each with the slide, the anchor it gave and whether
  that is the community anchor now.
- **A stock is data (R-1404).** Each stock is a record: page (A4 or US Letter), label width and height, columns, rows,
  top and left margin, horizontal and vertical pitch, corner radius, where each number comes from (datasheet,
  template, die drawing), and its warnings. The first stocks are dossier 16's proposal: the plain-paper grids (20 x 26
  mm labels with 2 mm gutters, 72 upright on A4 and 77 on their side on US Letter, centred on the page, with cut
  marks), Diversified Biotech MISL-1000 (US Letter, 8 x 12, 22.2 mm squares), LabTAG CLA-4WH (US Letter, 6 x 13, 23.9 x
  19.6 mm, the one that fits inside the 20 mm label end), and the 66-up 25.4 mm A4 layout shared by HERMA 8831 and
  10107 and LabTAG A4CL-112. A stock whose template rows are closer than its nominal height (CLA-4WH's 19.49 mm pitch
  for a 19.6 mm label) is drawn within the smaller of the two.
- **One label, any cell (R-1405).** The label is U11's frosted-end label fitted to the cell: the collection's hue band,
  the catalogue number, the name, then the data lines while they fit, and the QR with its four-module quiet zone,
  which no text enters. A cell taller than wide takes the QR at its foot, as the slide's label end does; a wider cell
  takes it on the right. The QR is 14 mm, shrinking to no less than 11 mm (29 modules of 0.3 mm with the quiet zone)
  to let text fit. Content keeps 0.8 mm inside the label's edge, since printers and stocks both drift.
- **Printing onto stock.** Nothing is drawn outside the labels, and no outline on stock (it would print on the labels);
  the plain-paper grid has a dashed cut line around each label, in its gutters. The sheet starts at a chosen position
  (to use a part-used sheet) and moves by a printer offset in 0.1 mm steps, which the page keeps on the device per
  stock (the offset belongs to the printer, not the account). The test page draws every label's outline, the stock's name and the instruction to
  print at 100 % on plain paper and hold it against a sheet, as Diversified Biotech's instructions ask. Laser toner
  on stock is not xylene-proof (LabTAG's own test): the dialog says so, and a 25.4 mm label is wider than a US slide.
- **Anyone prints a published slide's labels**, as anyone opens its single sheet (U11); a sheet takes up to 500
  slides.
- **The export (R-1407)** is one's own: `GET /api/people/me/slides.csv`, one row per slide of the account (any status),
  with its exact place, as iNaturalist leaves `private_` columns empty for anyone who may not see them.
