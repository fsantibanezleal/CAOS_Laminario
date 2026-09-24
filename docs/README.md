# Laminario documentation

Laminario is an open collection of microscope slides. Each case is a slide, shown as the glass object it is, with
its macro image, a label carrying a QR code, and its micro imagery in deep zoom. Visitors explore without an
account; invited contributors add slides; the community agrees on identifications.

This wiki is written as the product is built, unit by unit. Each section documents only what exists.

| Section | What it holds |
|---|---|
| [design/](design/SDD.md) | The software design document, written before any code, and one feature design per unit under `design/features/` (requirements with the gate that verifies each, the design, the tasks and the convergence verdict). |
| [architecture](architecture.md) | How the system is put together: the processes, the lanes, the data locations. |
| [guides](guides.md) | How to run it, test it and work on it. |

## What Laminario is, and what it is not

It **is** a public, browsable collection of microscope slides across living things, rocks, minerals and
crystals, with the provenance and licence of every image, deep zoom over the IIIF standard, and a way for invited
contributors to add their own slides, including whole-slide scanner files.

It **is not** an identification service (no automated species or mineral identification), a diagnostic tool, a
fluorescence or volume viewer, or a place for images without a licence that allows reuse. The full list of
non-goals is in section 1 of the [design document](design/SDD.md).
