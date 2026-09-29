// About the collection, in English (U15). Transcribed from the wiki (pages 04, 05, 13, 15) and dossiers 16 and 17 of the
// planning record; content.es.ts carries the same blocks in Spanish.
import type { AboutContent } from "./model";

const TASL_EXAMPLE = "\"Polyplax borealis, slide NHMUK010173454\" by The Trustees of the Natural History Museum, London, "
  + "from data.nhm.ac.uk, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); adapted: re-encoded as a tiled "
  + "pyramid.";
const CITE_EXAMPLE = "Laminario (2026). Polyplax borealis (NHMUK010173454), whole mount [Microscope slide]. "
  + "https://laminario.ml.fasl-work.com/s/7K2QD4MN. Read on 29 September 2026.";

export const aboutEn: AboutContent = {
  title: "About the collection",
  lead: "Laminario is a collection of microscope slides kept as a museum keeps them: in cabinets, drawer by drawer, "
    + "each slide with its label. Anyone may look; invited people contribute slides and identify them.",
  contents: "On this page",
  sections: [
    {
      id: "what", title: "What Laminario is", blocks: [
        { kind: "p", text: ["A slide is the record. Each carries what a museum label carries (the name, where and when "
          + "the specimen was collected, who prepared it and how) and its images: photographs of the slide and of the "
          + "specimen, and the views under the microscope, from a single field to a whole-slide scan or a stack of "
          + "focal planes."] },
        { kind: "p", text: ["The collection is arranged in realms (life, earth and matter), cabinets and drawers. A "
          + "drawer takes a slide by what it shows: a taxon of the GBIF Backbone, a mineral of the IMA list, a rock of "
          + "the British Geological Survey's scheme, a crystal, a material. Every slide has a label to print, with a QR "
          + "code that opens its page."] },
        { kind: "p", text: ["It began with a base collection from open sources, each image processed by the same "
          + "pipeline a contribution goes through, and it grows with contributions that the community identifies."] },
      ],
    },
    {
      id: "numbers", title: "The collection today", blocks: [
        { kind: "p", text: ["Counted from the database when this page was opened."] },
        { kind: "live", what: "numbers" },
      ],
    },
    {
      id: "sources", title: "Where the images come from", blocks: [
        { kind: "p", text: ["Every image of the base collection was downloaded once from its source, with its SHA-256 "
          + "recorded, and is kept with its source's record, its author or rights holder, and its licence. Each "
          + "slide's page shows them beside the image. The table counts the images of published slides by source."] },
        { kind: "live", what: "sources" },
      ],
    },
    {
      id: "licences", title: "The licences", blocks: [
        { kind: "p", text: ["Each image keeps its own licence. The base collection takes only licences that allow any "
          + "use, commercial use included, with credit where the licence asks for it: CC0, the Public Domain Mark, No "
          + "Known Copyright, CC BY and CC BY-SA. A contributor may also choose CC BY-NC or CC BY-NC-SA, as on "
          + "iNaturalist."] },
        { kind: "live", what: "licences" },
        { kind: "p", text: ["The licences give no warranties and may not give every permission a use needs: privacy "
          + "and publicity rights, for instance, are not licensed. The terms are the deeds and legal codes at ",
          { a: "creativecommons.org", href: "https://creativecommons.org/licenses/" },
          " and the statement at ", { a: "rightsstatements.org", href: "https://rightsstatements.org/page/NKC/1.0/" },
          "; this page summarises them."] },
      ],
    },
    {
      id: "cite", title: "How to cite and to credit", blocks: [
        { kind: "p", text: ["To credit an image, give its title, author, source and licence, as Creative Commons ",
          { a: "recommends", href: "https://wiki.creativecommons.org/wiki/Recommended_practices_for_attribution" },
          " (TASL), with a link to the licence, and say that the image is adapted: every image Laminario serves is "
          + "re-encoded as a tiled pyramid or fused from a focal stack. Each slide's page gives these lines ready to "
          + "copy, under ", { strong: "Cite this slide" }, ". For example:"] },
        { kind: "code", text: TASL_EXAMPLE },
        { kind: "p", text: ["To cite a slide, in the form the Natural History Museum's Data Portal uses for a ",
          { a: "record", href: "https://data.nhm.ac.uk/about/citation" }, ":"] },
        { kind: "code", text: CITE_EXAMPLE },
        { kind: "p", text: ["When you use images of the base collection, credit their sources first (the museum or the "
          + "author) and Laminario as where you found them. Images under CC0 or the Public Domain Mark need no credit; "
          + "Creative Commons recommends naming the institution that holds them all the same."] },
      ],
    },
    {
      id: "imaging", title: "How an image becomes a stage", blocks: [
        { kind: "h3", text: "Reading a file" },
        { kind: "p", text: ["libvips (Martinez and Cupitt, 2005) reads the scanners' formats through OpenSlide (Goode "
          + "et al., 2013) and every other image through its own loaders. From the headers alone, before a pixel is "
          + "decoded, Laminario reads the image's size and levels, its pixel size in micrometres, the scanner's "
          + "photographs of the label and the glass, and the focal planes of a stack. A file whose header claims more "
          + "than 200,000 pixels on a side is refused before it is opened."] },
        { kind: "p", text: ["A pixel size is taken only from a calibration: the scanner's own, ImageJ's when its unit is "
          + "the micron, or TIFF resolution tags in the microscopy range (at least 100 pixels per millimetre). A "
          + "camera's nominal density, 72, 96 or 300 dpi, says nothing about the specimen and is ignored."] },
        { kind: "h3", text: "One pyramid per plane" },
        { kind: "p", text: ["Each image is written as one tiled, pyramidal TIFF: tiles of 512 pixels, the full image at "
          + "level 0 and every half-size level below it until the image fits one tile. An image whose long side is ",
          { m: "n" }, " pixels has"] },
        { kind: "math", tex: "L = \\left\\lceil \\log_2 \\frac{n}{512} \\right\\rceil + 1" },
        { kind: "p", text: ["levels. A viewer asks only for the tiles of the level that matches its zoom, so a scan of "
          + "46,000 by 32,914 pixels opens as quickly as a photograph."] },
        { kind: "figure", figure: "pyramid", caption: ["The levels of a pyramid: each half the size of the one above, "
          + "cut in tiles of 512 pixels. The viewer reads the tiles of one level, only where it looks."] },
        { kind: "h3", text: "Fidelity, measured" },
        { kind: "p", text: ["The written image is compared with its source on 32 regions of 512 by 512 pixels:"] },
        { kind: "math", tex: "\\mathrm{PSNR} = 10 \\log_{10} \\frac{255^2}{\\mathrm{MSE}}, \\qquad "
          + "\\mathrm{MSE} = \\frac{1}{N}\\sum_i (x_i - y_i)^2" },
        { kind: "p", text: ["The mean must reach 38 dB. JPEG at quality 85 is the default. It keeps colour at half "
          + "resolution, which is invisible on most specimens but not on a thin section between crossed polars, whose "
          + "interference colours are the diagnostic detail (32.1 dB on a Commons thin section). Such an image is "
          + "written again at quality 90, where libvips keeps colour at full resolution (49.9 dB)."] },
        { kind: "h3", text: "Tiles over IIIF" },
        { kind: "p", text: ["The pixels reach the browser through the ",
          { a: "IIIF Image API 3.0", href: "https://iiif.io/api/image/3.0/" },
          ", served by iipsrv from the pyramid files. A request names a region, a size, a rotation and a quality:"] },
        { kind: "code", text: "/iiif/{identifier}/{region}/{size}/{rotation}/{quality}.jpg" },
        { kind: "p", text: ["A deep-zoom viewer such as OpenSeadragon asks only for tiles: one tile of one level of the "
          + "pyramid. Any IIIF viewer can open a Laminario slide through its manifest (the ",
          { a: "IIIF Presentation API 3.0", href: "https://iiif.io/api/presentation/3.0/" },
          "), and a tile is served only while its slide is published."] },
        { kind: "h3", text: "The pixel size and the objectives" },
        { kind: "p", text: ["Scanners pair an objective with a pixel size whose product is close to 10 micrometres (20x "
          + "at 0.5 µm, 40x at 0.25 µm). At objective ", { m: "M" }, " a screen pixel covers ", { m: "10/M" },
          " µm, so an image whose pixel covers ", { m: "p" }, " µm is shown at"] },
        { kind: "math", tex: "z = \\frac{p \\cdot M}{10}" },
        { kind: "p", text: ["screen pixels per image pixel. The stage offers 2x to 100x; a step beyond the image's own "
          + "resolution is labelled digital zoom, and an image without a pixel size offers free zoom only and says it "
          + "is not to scale. The scale bar is the longest length of the 1, 2, 5 series that fits a quarter of the "
          + "view."] },
        { kind: "figure", figure: "objectives", caption: ["One image at three objectives: the same 0.5 µm pixel drawn "
          + "over more screen pixels as the objective grows; past the image's own resolution the zoom is digital."] },
        { kind: "h3", text: "Focal stacks" },
        { kind: "p", text: ["A focal stack shows each part of a thick specimen sharp in a different plane. Up to 500 MB, "
          + "a stack is kept whole; above that, ", { m: "k = 11" }, " of its ", { m: "n" },
          " planes are kept, evenly spaced and including both ends:"] },
        { kind: "math", tex: "i_j = \\operatorname{round}\\left( j \\, \\frac{n - 1}{k - 1} \\right), \\qquad "
          + "j = 0, \\ldots, k-1" },
        { kind: "p", text: ["Each kept plane keeps its original index and depth, so the stage names real focal "
          + "depths."] },
        { kind: "h3", text: "All in focus" },
        { kind: "p", text: ["Extended depth of field builds one image sharp everywhere, and a height map: for each "
          + "pixel, the plane it came from, which with the planes' depths is a map of the specimen's surface. "
          + "Laminario follows the EPFL plugin (Forster, Van De Ville, Berent, Sage and Unser, 2004) with its two "
          + "methods. Variance selection takes, at each pixel, the plane whose 5 by 5 neighbourhood varies most:"] },
        { kind: "math", tex: "\\sigma_k^2(p) = \\sum_{q \\in N(p)} \\big(I_k(q) - \\mu_k(p)\\big)^2, \\qquad "
          + "h(p) = \\arg\\max_k \\sigma_k^2(p)" },
        { kind: "p", text: ["Complex wavelet fusion keeps, at every coefficient of a complex wavelet transform, the plane "
          + "of greatest modulus, makes neighbouring choices agree, inverts the transform and gives each pixel the "
          + "measured value nearest to the result. On stacks whose true focus is known, the variance map is within one "
          + "plane of the truth on 99.9 percent of pixels; the stage shows the wavelet composite and reads depths "
          + "from the variance map."] },
        { kind: "p", text: ["The plugin's consistency checks take an image's height for its width, which on a "
          + "non-square stack sends them to the wrong regions. Laminario uses the true geometry, right three times as "
          + "often on non-square synthetic stacks, and keeps the plugin's convention as an option, with which its "
          + "output equals the plugin's on every pixel."] },
        { kind: "figure", figure: "stack", caption: ["A focal stack, and what fusion makes of it: each region sharp in "
          + "its own plane, one composite sharp everywhere, and the height map of the plane each pixel came from."] },
        { kind: "h3", text: "Polarised pairs" },
        { kind: "p", text: ["A thin section of a rock is photographed twice on one field: in plane-polarised light, and "
          + "between crossed polars, where minerals show their interference colours. The stage opens both, fades one "
          + "over the other and turns the view in quarter turns."] },
        { kind: "figure", figure: "polarised", caption: ["A polarised pair: the polariser below the section and, for "
          + "crossed polars, the analyser above it at a right angle."] },
        { kind: "h3", text: "No position leaves the server" },
        { kind: "p", text: ["Every derivative keeps only the colour profile: no EXIF, XMP or IPTC, so no GPS position a "
          + "camera wrote. A photograph's position is read in the browser before upload and shown to its contributor, "
          + "who decides whether the place is open, obscured or private."] },
      ],
    },
    {
      id: "community", title: "Identification", blocks: [
        { kind: "p", text: ["Identifiers say what a slide shows, and the name most of them agree on becomes the slide's. "
          + "The rule is ", { a: "iNaturalist's community taxon", href: "https://github.com/inaturalist/inaturalist" },
          ", applied to every kind of anchor through its lineage. For every node ", { m: "t" }, ", with ",
          { m: "c(t)" }, " the identifications of ", { m: "t" }, " or below it, ", { m: "d(t)" },
          " those outside its branch, and ", { m: "a(t)" }, " the explicit disagreements of an ancestor,"] },
        { kind: "math", tex: "\\mathrm{score}(t) = \\frac{c(t)}{c(t) + d(t) + a(t)}" },
        { kind: "p", text: ["The community anchor is the deepest node with at least two identifications and a score "
          + "above two thirds. A slide is verified when that anchor is as fine as its kind needs, needs identification "
          + "until then, and is a reference slide when one of its checks fails: every base scan without a pixel size "
          + "is one, since a slide without a scale cannot support a measurement. Curators resolve flags and may hide an "
          + "item with a reason; every hiding and restoring is kept."] },
      ],
    },
    {
      id: "privacy", title: "What is never shown", blocks: [
        { kind: "list", items: [
          ["An account's email. Profiles, slides and identifications name people by their display name and handle."],
          ["The exact place of an obscured slide. Its public record gives the 0.2 degree cell it lies in (about 22 km "
            + "from south to north) and a fixed point inside that depends only on the cell and the slide, never on "
            + "where the true point lies, so no two answers can be combined to narrow it down."],
          ["Any place of a private slide beyond its locality text and country."],
          ["A camera's metadata: every derivative is written without EXIF, XMP or IPTC."],
        ] },
        { kind: "p", text: ["A contributor's own export carries the exact places of their slides; no one else's "
          + "does."] },
        { kind: "figure", figure: "geoprivacy", caption: ["An open slide at its point; an obscured one as its 0.2 degree "
          + "cell with a public point inside; a private one with no point at all."] },
      ],
    },
    {
      id: "names", title: "The names behind the tree", blocks: [
        { kind: "p", text: ["The tree places a slide by its anchor's lineage, and each kind of anchor has its "
          + "authority. The Rock Classification Scheme's names and hierarchy are used as facts; its reports are cited, "
          + "not copied."] },
        { kind: "live", what: "vocabularies" },
      ],
    },
    {
      id: "software", title: "Software, fonts and map data", blocks: [
        { kind: "p", text: ["Laminario is built on open software, and each piece keeps its licence. The tile server "
          + "(iipsrv) and the imaging libraries (libvips, OpenSlide) run as their own programs, unmodified. The "
          + "collection icons and the interface glyphs are drawn for Laminario."] },
        { kind: "live", what: "software" },
        { kind: "live", what: "fonts" },
        { kind: "p", text: ["The map's data: © OpenStreetMap contributors, under the Open Database License, from a "
          + "Protomaps extract. The map's corner links to ",
          { a: "OpenStreetMap's copyright page", href: "https://www.openstreetmap.org/copyright" }, "."] },
        { kind: "live", what: "map" },
      ],
    },
    {
      id: "references", title: "References", blocks: [
        { kind: "list", items: [
          ["Forster B, Van De Ville D, Berent J, Sage D, Unser M (2004). Complex wavelets for extended depth-of-field: "
            + "a new method for the fusion of multichannel microscopy images. Microscopy Research and Technique "
            + "65(1-2): 33-42. ", { a: "doi:10.1002/jemt.20092", href: "https://doi.org/10.1002/jemt.20092" }],
          ["Goode A, Gilbert B, Harkes J, Jukic D, Satyanarayanan M (2013). OpenSlide: a vendor-neutral software "
            + "foundation for digital pathology. Journal of Pathology Informatics 4: 27. ",
            { a: "doi:10.4103/2153-3539.119005", href: "https://doi.org/10.4103/2153-3539.119005" }],
          ["Martinez K, Cupitt J (2005). VIPS, a highly tuned image processing software architecture. IEEE "
            + "International Conference on Image Processing 2005, II-574. ",
            { a: "doi:10.1109/ICIP.2005.1530120", href: "https://doi.org/10.1109/ICIP.2005.1530120" }],
          ["Scott B, Baker E, Woodburn M, Vincent S, Hardy H, Smith VS (2019). The Natural History Museum Data Portal. "
            + "Database 2019: baz038. ",
            { a: "doi:10.1093/database/baz038", href: "https://doi.org/10.1093/database/baz038" }],
          ["Kikuchi K, Kameda T, Higuchi K, Yamashita A (2013). A global classification of snow crystals, ice "
            + "crystals, and solid precipitation based on observations from middle latitudes to polar regions. "
            + "Atmospheric Research 132-133: 460-472. ",
            { a: "doi:10.1016/j.atmosres.2013.06.006", href: "https://doi.org/10.1016/j.atmosres.2013.06.006" }],
          ["GBIF Secretariat (2023). GBIF Backbone Taxonomy. Checklist dataset. ",
            { a: "doi:10.15468/39omei", href: "https://doi.org/10.15468/39omei" }],
        ] },
      ],
    },
  ],
  sources: {
    commons: ["Files of Wikimedia Commons, each under the licence its author chose, read from the file's own "
      + "metadata. The credit is the author's name as Commons gives it, without the file page's templates."],
    nhm: ["Specimen images of the Natural History Museum's Data Portal, London: slide-mounted lice and other insects "
      + "photographed and scanned by the museum, shared under CC BY 4.0, rights holder the Trustees of the Natural "
      + "History Museum, London."],
    smithsonian: ["Records of Smithsonian Open Access, dedicated to the public domain (CC0), among them the snow "
      + "crystals Wilson Bentley photographed through a microscope, kept by the Smithsonian Institution Archives."],
    zenodo: ["Whole-slide focal stacks of the Smithsonian's National Museum of Natural History, published on Zenodo "
      + "under CC BY 4.0, each with its DOI and its creators."],
    openslide: ["Samples of the OpenSlide test data, CC0: lymph node sections of the CAMELYON16 data set "
      + "(Computational Pathology Group, Radboud University Medical Center) and a bone marrow smear scanned by Maki "
      + "Sakuma (National Center for Global Health and Medicine, doi:10.5061/dryad.6m905qfzx)."],
    contribution: ["Slides contributed by the people of Laminario, each image under the licence its contributor "
      + "chose."],
    other: ["Images whose source this page does not describe yet."],
  },
  licences: {
    cc0: { name: "CC0 1.0 (public domain dedication)", text: ["Copy, modify, distribute and perform it, even "
      + "commercially, without asking permission. Credit is not required; naming the author and the source is a "
      + "courtesy."] },
    pdm: { name: "Public Domain Mark 1.0", text: ["Identified as free of known copyright restrictions: the same "
      + "freedoms as CC0, though the status may differ in some countries."] },
    nkc: { name: "No Known Copyright", text: ["The holding organisation believes the item is not restricted by "
      + "copyright but could not determine it conclusively. A statement, not a licence."] },
    by: { name: "CC BY (Attribution)", text: ["Share and adapt for any purpose, even commercially, giving appropriate "
      + "credit, linking the licence and saying if changes were made."] },
    "by-sa": { name: "CC BY-SA (Attribution-ShareAlike)", text: ["As CC BY, and adaptations must be shared under the "
      + "same licence."] },
    "by-nc": { name: "CC BY-NC (Attribution-NonCommercial)", text: ["Share and adapt with credit, but not for use "
      + "primarily intended for commercial advantage or monetary compensation."] },
    "by-nc-sa": { name: "CC BY-NC-SA (Attribution-NonCommercial-ShareAlike)", text: ["As CC BY-NC, and adaptations "
      + "under the same licence."] },
  },
  figures: {
    pyramid: { level: "Level", tile: "tile of 512 px", full: "full resolution", half: "each level half the one above",
      title: "The levels of a tiled pyramid" },
    objectives: { screen: "screen pixels per image pixel", digital: "digital zoom", image: "image pixel, 0.5 µm",
      title: "One image at three objectives" },
    stack: { planes: "focal planes", composite: "all in focus", height: "height map", title: "A focal stack fused" },
    polarised: { light: "light", polariser: "polariser", section: "thin section", analyser: "analyser",
      ppl: "plane-polarised", xpl: "crossed polars", title: "A polarised pair" },
    geoprivacy: { open: "open: the point", obscured: "obscured: the 0.2 degree cell, a public point",
      private: "private: no point", title: "Geoprivacy" },
  },
  live: {
    slides: "Published slides", base: "from the base collection", contribution: "contributed", wsi: "whole-slide scans",
    images: "images", countries: "countries", contributors: "contributors", identifications: "identifications by the "
      + "community", realm: "Realm", collections: "collections", source: "Source", images_col: "Images",
    slides_col: "Slides", licences_col: "Licences", licence: "Licence", allows: "What it allows", read: "Counted at",
    name: "Name", citation: "Citation", licence_col: "Licence", none: "cited", software: "Software",
    fonts: "Fonts", map: "Map data", failed: "The numbers could not be read. Try again in a moment.",
    terms: "terms",
    contributions: "Contributions", others: "Other sources",
  },
};
