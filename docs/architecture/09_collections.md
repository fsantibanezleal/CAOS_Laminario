# 09 · The collection tree

![A slide's anchor resolves to facts through the GBIF backbone or a vocabulary; placement walks down the tree from the realms, taking the accepting child of highest priority; the guard checks the tree before it is served](svg/collections.svg)

A visitor browses slides as a museum is walked: realm, collection, sub-collection, group. Under that tree every
slide is anchored to a real classification, a taxon of the GBIF backbone, a rock name of the British Geological
Survey scheme, a mineral of the IMA list, a crystal origin, a material. The tree is a curation layer over those
anchors, and each node carries a rule that says which anchors it takes. The whole tree, node by node, is
[docs/collections/tree.md](../collections/tree.md), generated from the file the product serves.

## 1. Levels, facets and counts

**Realm > Collection > Sub-collection > Group > Slide.** Groups exist where the domain has a standard finer
division (bacterial phyla, igneous grain-size groups, silicate subclasses, snow-crystal categories). Three
properties cut across the tree and are **facets**, not levels: the preparation (ten types), the imaging modality
(nine), and for plants the organ (nine); crystals have their crystal system (seven).

| Realm | Collections | Sub-collections and groups |
|---|---|---|
| Life | 13: plants, fungi and lichens, microbes, insects, arachnids and other arthropods, molluscs, other invertebrates, fishes, amphibians, reptiles, birds, mammals, pollen and spores | 72 |
| Earth | 3: fossils and microfossils, rocks, minerals | 41 |
| Matter | 2: crystals, materials | 17 |

Vertebrate slides are prepared by tissue, not by order, so the five vertebrate collections share one set of ten organ
systems (integument, blood and immune, development, respiratory, digestive, circulatory, nervous and sensory,
musculoskeletal, urogenital, and the Parasites and hosts view), counted once, like their icons, plus seven
class-specific sub-collections (feathers, eggshell, hair, gills, otoliths, tadpoles, scales). In all 191 nodes, 130
sub-collections and groups by the dossier's count.

The design document planned 129 and 185 icons. The igneous rocks gained a fourth group because the scheme itself
classifies the "exotic" crystalline rocks apart (lamprophyres, carbonatites, kimberlites, lamproites, and the
melilitic, kalsilitic and leucitic rocks, its Figure 1), and no grain-size group fits them.

## 2. Anchors

| Kind | Reference | Resolved to | Source and licence |
|---|---|---|---|
| taxon | GBIF usage key | the lineage: the keys of every ancestor | GBIF Backbone Taxonomy, CC BY 4.0 |
| mineral | IMA name (or a group name: olivine, biotite, plagioclase) | the Nickel-Strunz code as a path, `9.AF.15` as `9.A.F.15` | the IMA list, CC BY-SA 3.0; codes from Wikidata, CC0 |
| rock | a BGS Rock Classification Scheme name, a meteorite class, a Laminario term | the family, `igneous.coarse` | BGS RCS volumes 1 to 3; Weisberg et al. (2006) |
| crystal | origin, or origin/system: `ice/hexagonal` | `ice`, or `ice.P` with the snow-crystal category | Kikuchi et al. (2013) |
| material | a controlled term: `cotton`, `potato-starch` | the family, `fibre` | Laminario |

**Taxa.** A key is read once from GBIF (`/v1/species/{key}` and `/parents`) and kept in the `taxon` table, so a slide
is placed again, years later, with the lineage it was placed with, and without the network. A synonym is followed to
its accepted taxon; a key of another checklist is refused, because the rules speak of backbone taxa. The backbone
is used as it is, and it is not always the textbook: it has no Phthiraptera (lice are placed by their 26 families
inside Psocodea), no Actinopterygii (ray-finned fish orders sit directly under Chordata, so Fishes is the chordates
less the tetrapods, tunicates and lancelets), no Reptilia (its four classes are Squamata, Testudines, Crocodylia and
Sphenodontia), and it still names the bacterial phyla Firmicutes, Actinobacteriota and Proteobacteria.

**Minerals.** The IMA list gives 6,200 valid species, exactly the count it states, but no classification. Wikidata
carries the Nickel-Strunz codes of 4,808 of them under CC0, and group names take their code from their own item or
from a named member (olivine from forsterite, `9.AC.05`). A species without a code needs its class declared in
`anchor.classification`; a declared class that contradicts the table is refused. The file is rebuilt from the two
sources in the data vault by `scripts/build_minerals.py`, and the rebuild must match (R-706). Nickel-Strunz has ten
classes, the tenth the organic compounds (whewellite, weddellite); silicates split by the division letter: A
nesosilicates, B sorosilicates, C cyclosilicates, D inosilicates, E phyllosilicates, F and G tectosilicates.

**Rocks.** 365 names: the 229 names of the igneous appendix with their group codes, the 54 metamorphic root names
with their sections, 52 sedimentary names by section, 18 meteorite classes and 7 Laminario terms. Every scheme name
is found in its volume by `scripts/check_rock_terms.py` (R-707). Metamorphic names go to the foliated or non-foliated
group only when the scheme defines them by fabric (slate, schist, gneiss, the mylonites; granofels, hornfels, marble,
quartzite, the cataclastic and metasomatic rocks); names defined by protolith or composition (pelite, amphibolite,
eclogite) stay at the metamorphic level. Unconsolidated sediments go to Soils and sediments.

**Parts and preservation.** `specimen.part` names the tissue or organ a slide shows (blood, feather, gill, pollen,
leaf); `specimen.preservation` says whether the specimen is recent, fossil, or in amber or copal. Only organisms have
either.

## 3. Rules

A rule is a set of **clauses**, alternatives each of which is a conjunction. A slide is described by its facts:
kind $k$, key $\kappa$ and lineage $\Lambda$ (the keys of the taxon and all its ancestors), vocabulary path $\pi$, part
$p$ and preservation $q$. A clause $c = (K, T, X, P, Q, R)$ holds for a slide when

$$
\begin{aligned}
&(K = \varnothing \lor k \in K) \;\land\; (T = \varnothing \lor T \cap \Lambda \neq \varnothing) \\
&\land\; \forall x \in X:\; x \notin \Lambda \,\land\, \kappa \notin A(x) \\
&\land\; (P = \varnothing \lor \exists\, \rho \in P:\ \rho \sqsubseteq \pi) \;\land\; (Q = \top \lor p \in Q) \;\land\; (R = \top \lor q \in R)
\end{aligned}
$$

where $A(x)$ is the set of ancestors of the excluded taxon $x$ and $\rho \sqsubseteq \pi$ means that $\rho$ is a prefix of
$\pi$ segment by segment (`1` is not a prefix of `10.A`). The exclusion has two halves: the slide's taxon may not lie
inside an excluded clade, and it may not contain one. "Insects other than beetles" does not take the class Insecta,
which would claim the beetles too, so an anchor at class level stays with Insects, and an anchor "Animalia" stays at
the realm Life.

A node **accepts** a slide when one of its clauses holds; a **container** (a node with children and no condition on
the anchor, such as Pollen and spores) accepts when one of its children does. A **view** (Parasites and hosts) accepts
nothing: it shows the slides whose recorded host lies inside its collection.

## 4. Placement

The suggestion is found by walking down: at each level the children that accept the slide are candidates, and the one
of highest priority is taken,

$$
n_{i+1} = \operatorname*{arg\,max}_{m \,\in\, \mathrm{children}(n_i),\ \mathrm{acc}(m,\,s)} \mathrm{priority}(m),
$$

until no child accepts. The guard (section 5) guarantees the maximum is unique, so the walk never depends on the
order the siblings are written in; the gate places every real anchor of its table and a witness of every node on the
tree and on a copy with every list of siblings reversed, and requires the same answers (R-062).

The **accepting** nodes are those that, with all their ancestors, accept the slide. A pine pollen slide is suggested
at Pollen and spores > Gymnosperm pollen, and Plants > Conifers accepts it too; a contributor may choose either.
Anywhere else needs a curator, with a reason that is kept (R-702). On submission the API resolves the anchor and the
host, checks the part and the placement, and answers with the contract's error shape: the field, what was wrong, what
was expected (R-701). When GBIF does not answer, it says so with 503 instead of guessing.

## 5. The guard

Before the tree is served the guard checks (R-060, R-061):

- every node: an id of lower-case words, the level its depth implies, a name and a description in English and
  Spanish, an icon of the sprite, a rule whose taxa are in the lock, whose paths exist in their vocabulary and whose
  parts are in the part vocabulary;
- every node is **reachable**: hypothetical slides built from its rule (for a taxon, a species inside the clade and
  outside every exclusion) are placed at it or below it;
- no two siblings can take the same slide with the same priority.

The overlap test is symbolic. Two clauses intersect when every dimension admits a common value: kinds, parts and
preservations share an element; paths are prefix-comparable; and for taxa, one clause's clade contains the other's
and the deeper one is not excluded by the other clause (clades are nested or disjoint). The test can only err toward
reporting an overlap (a set of exclusions that together cover a whole clade is not recognised), never toward missing
one, which is what makes a passing guard a proof that the walk has no ties.

Where the tree means an overlap, it says so with a priority: lichens over sac fungi, apicomplexans and blood parasites
(with the trypanosomes) over flagellates, pollen and spores over plants and fungi, fossil palynomorphs over fossil
plants and fungi, the class-specific sub-collections over the shared organ systems.

## 6. The API

| Route | What |
|---|---|
| `GET /api/collections` | the tree with published-slide counts (views count the slides they show) |
| `GET /api/collections/{id}` | one node, its children, the path from its realm |
| `GET /api/collections/{id}/iiif` | the node as a IIIF Presentation 3 Collection: child collections, then the manifests placed at it (R-703) |
| `GET /api/facets` | the four facets with the icon of each value |
| `GET /api/anchors/search?kind=&q=` | names for the anchor field: GBIF backbone suggestions, or a vocabulary |
| `POST /api/placement` | the suggestion, its path and the accepting nodes for an anchor |
| `GET /api/slides?node=` | published slides under a node, or shown by a view |

Every manifest's `partOf` is the IIIF Collection of its node, so any IIIF client can climb from a slide to its
collection and down again.

## 7. Icons

186 icons: 3 realms, 18 collections, 130 sub-collections and groups, and 35 facet values. Each draws its subject as
it looks under the lens (barbs and barbules for feathers, cuticle and medulla for hair, interlocking grains for a
coarse igneous rock, a unit form for a crystal system). They are hand-drawn in one sprite
(`frontend/src/icons/sprite.svg`) on a 32-unit grid; the build (`scripts/build_icons.py`) adds what every icon of a
kind shares, so it is the same by construction: the stroke (1.75 units, round caps and joins, the page's colour), the
frame (the field-of-view circle for a place, with four reticle ticks for a realm; a rounded square for a facet), and
the titles in English and Spanish from the tree. The gate samples every path, curve and arc and requires the drawing
to stay inside its frame's clear area, with no other stroke weight and no colour of its own (R-704). The contact
sheet shows every icon at 48 and 16 pixels:

![All 186 icons at 48 and 16 pixels](../collections/svg/icons.svg)

## References

- GBIF Secretariat. GBIF Backbone Taxonomy. Checklist dataset `d7dddbf4-2cf0-4f39-9b2a-bb099caae36c`, CC BY 4.0,
  accessed through https://api.gbif.org/v1.
- Pasero M et al. The New IMA List of Minerals, a work in progress, updated January 2026. IMA Commission on New
  Minerals, Nomenclature and Classification, CC BY-SA 3.0.
- Strunz H, Nickel EH (2001). Strunz Mineralogical Tables, 9th edition. Schweizerbart. Codes as carried by Wikidata
  properties P712 and P713 (CC0).
- Gillespie MR, Styles MT (1999). BGS Rock Classification Scheme, Volume 1: Classification of igneous rocks, 2nd
  edition. British Geological Survey Research Report RR 99-06. https://nora.nerc.ac.uk/3223/
- Robertson S (1999). BGS Rock Classification Scheme, Volume 2: Classification of metamorphic rocks. RR 99-02.
  https://nora.nerc.ac.uk/id/eprint/3226/
- Hallsworth CR, Knox RWO'B (1999). BGS Rock Classification Scheme, Volume 3: Classification of sediments and
  sedimentary rocks. RR 99-03. http://nora.nerc.ac.uk/3227/
- Weisberg MK, McCoy TJ, Krot AN (2006). Systematics and evaluation of meteorite classification. In Meteorites and
  the Early Solar System II, 19-52. doi:10.2307/j.ctv1v7zdmm.8
- Kikuchi K, Kameda T, Higuchi K, Yamashita A (2013). A global classification of snow crystals, ice crystals, and
  solid precipitation based on observations from middle latitudes to polar regions. Atmospheric Research 132-133,
  460-472. doi:10.1016/j.atmosres.2013.06.006
- Le Maitre RW et al. (2002). Igneous Rocks: A Classification and Glossary of Terms, 2nd edition. Cambridge
  University Press. doi:10.1017/CBO9780511535581
