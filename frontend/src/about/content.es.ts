// Acerca de la colección, en español (U15): los mismos bloques, ecuaciones, figuras y enlaces que content.en.ts.
import type { AboutContent } from "./model";

const TASL_EXAMPLE = "\"Polyplax borealis, lámina NHMUK010173454\", de The Trustees of the Natural History Museum, "
  + "London, en data.nhm.ac.uk, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); adaptada: recodificada como "
  + "pirámide en teselas.";
const CITE_EXAMPLE = "Laminario (2026). Polyplax borealis (NHMUK010173454), montaje total [Lámina de microscopio]. "
  + "https://laminario.ml.fasl-work.com/s/7K2QD4MN. Consultada el 29 de septiembre de 2026.";

export const aboutEs: AboutContent = {
  title: "Acerca de la colección",
  lead: "Laminario es una colección de láminas de microscopio guardadas como las guarda un museo: en gabinetes, cajón "
    + "por cajón, cada lámina con su etiqueta. Cualquiera puede mirarlas; las personas invitadas aportan láminas y las "
    + "identifican.",
  contents: "En esta página",
  sections: [
    {
      id: "what", title: "Qué es Laminario", blocks: [
        { kind: "p", text: ["La lámina es el registro. Cada una lleva lo que lleva la etiqueta de un museo (el nombre, "
          + "dónde y cuándo se recolectó el espécimen, quién lo preparó y cómo) y sus imágenes: fotografías de la "
          + "lámina y del espécimen, y las vistas al microscopio, desde un campo único hasta un escaneo de lámina "
          + "completa o una pila de planos focales."] },
        { kind: "p", text: ["La colección se ordena en reinos (vida, tierra y materia), gabinetes y cajones. Un cajón "
          + "recibe una lámina por lo que muestra: un taxón del GBIF Backbone, un mineral de la lista de la IMA, una "
          + "roca del esquema del British Geological Survey, un cristal, un material. Cada lámina tiene una etiqueta "
          + "para imprimir, con un código QR que abre su página."] },
        { kind: "p", text: ["Comenzó con una colección base de fuentes abiertas, cada imagen procesada por el mismo "
          + "proceso por el que pasa un aporte, y crece con los aportes que la comunidad identifica."] },
      ],
    },
    {
      id: "numbers", title: "La colección hoy", blocks: [
        { kind: "p", text: ["Contada en la base de datos al abrir esta página."] },
        { kind: "live", what: "numbers" },
      ],
    },
    {
      id: "sources", title: "De dónde vienen las imágenes", blocks: [
        { kind: "p", text: ["Cada imagen de la colección base se descargó una vez desde su fuente, con su SHA-256 "
          + "registrado, y se guarda con el registro de la fuente, su autor o titular de derechos y su licencia. La "
          + "página de cada lámina los muestra junto a la imagen. La tabla cuenta las imágenes de las láminas "
          + "publicadas por fuente."] },
        { kind: "live", what: "sources" },
      ],
    },
    {
      id: "licences", title: "Las licencias", blocks: [
        { kind: "p", text: ["Cada imagen conserva su propia licencia. La colección base acepta solo licencias que "
          + "permiten cualquier uso, también el comercial, con reconocimiento cuando la licencia lo pide: CC0, la "
          + "Marca de Dominio Público, Sin Derechos de Autor Conocidos, CC BY y CC BY-SA. Quien aporta puede elegir "
          + "además CC BY-NC o CC BY-NC-SA, como en iNaturalist."] },
        { kind: "live", what: "licences" },
        { kind: "p", text: ["Las licencias no dan garantías y pueden no dar todos los permisos que un uso necesita: los "
          + "derechos de privacidad y de imagen, por ejemplo, no se licencian. Los términos son las escrituras y "
          + "textos legales de ", { a: "creativecommons.org", href: "https://creativecommons.org/licenses/" },
          " y la declaración de ", { a: "rightsstatements.org", href: "https://rightsstatements.org/page/NKC/1.0/" },
          "; esta página los resume."] },
      ],
    },
    {
      id: "cite", title: "Cómo citar y reconocer", blocks: [
        { kind: "p", text: ["Para reconocer una imagen, indique su título, autor, fuente y licencia, como ",
          { a: "recomienda", href: "https://wiki.creativecommons.org/wiki/Recommended_practices_for_attribution" },
          " Creative Commons (TASL), con un enlace a la licencia, e indique que la imagen está adaptada: toda imagen "
          + "que sirve Laminario está recodificada como pirámide en teselas o fusionada desde una pila focal. La "
          + "página de cada lámina da estas líneas listas para copiar, en ", { strong: "Citar esta lámina" },
          ". Por ejemplo:"] },
        { kind: "code", text: TASL_EXAMPLE },
        { kind: "p", text: ["Para citar una lámina, en la forma que usa el Portal de Datos del Natural History Museum "
          + "para un ", { a: "registro", href: "https://data.nhm.ac.uk/about/citation" }, ":"] },
        { kind: "code", text: CITE_EXAMPLE },
        { kind: "p", text: ["Al usar imágenes de la colección base, reconozca primero a sus fuentes (el museo o el "
          + "autor) y a Laminario como el lugar donde las encontró. Las imágenes en CC0 o con la Marca de Dominio "
          + "Público no requieren reconocimiento; aun así, Creative Commons recomienda nombrar a la institución que "
          + "las conserva."] },
      ],
    },
    {
      id: "imaging", title: "Cómo una imagen llega a la platina", blocks: [
        { kind: "h3", text: "Leer un archivo" },
        { kind: "p", text: ["libvips (Martinez y Cupitt, 2005) lee los formatos de los escáneres mediante OpenSlide "
          + "(Goode et al., 2013) y toda otra imagen con sus propios lectores. Solo con las cabeceras, antes de "
          + "decodificar un píxel, Laminario lee el tamaño y los niveles de la imagen, su tamaño de píxel en "
          + "micrómetros, las fotografías que el escáner toma de la etiqueta y del vidrio, y los planos focales de una "
          + "pila. Un archivo cuya cabecera declara más de 200.000 píxeles por lado se rechaza antes de abrirlo."] },
        { kind: "p", text: ["El tamaño de píxel se toma solo de una calibración: la del escáner, la de ImageJ cuando su "
          + "unidad es el micrón, o etiquetas de resolución TIFF en el rango de la microscopía (al menos 100 píxeles "
          + "por milímetro). La densidad nominal de una cámara, 72, 96 o 300 ppp, no dice nada del espécimen y se "
          + "ignora."] },
        { kind: "h3", text: "Una pirámide por plano" },
        { kind: "p", text: ["Cada imagen se escribe como un TIFF piramidal en teselas: teselas de 512 píxeles, la imagen "
          + "completa en el nivel 0 y cada nivel de la mitad de tamaño bajo él, hasta que la imagen cabe en una "
          + "tesela. Una imagen cuyo lado mayor mide ", { m: "n" }, " píxeles tiene"] },
        { kind: "math", tex: "L = \\left\\lceil \\log_2 \\frac{n}{512} \\right\\rceil + 1" },
        { kind: "p", text: ["niveles. Un visor pide solo las teselas del nivel que corresponde a su zoom, así un escaneo "
          + "de 46.000 por 32.914 píxeles se abre tan rápido como una fotografía."] },
        { kind: "figure", figure: "pyramid", caption: ["Los niveles de una pirámide: cada uno de la mitad del tamaño del "
          + "de arriba, cortado en teselas de 512 píxeles. El visor lee las teselas de un nivel, solo donde mira."] },
        { kind: "h3", text: "La fidelidad, medida" },
        { kind: "p", text: ["La imagen escrita se compara con su fuente en 32 regiones de 512 por 512 píxeles:"] },
        { kind: "math", tex: "\\mathrm{PSNR} = 10 \\log_{10} \\frac{255^2}{\\mathrm{MSE}}, \\qquad "
          + "\\mathrm{MSE} = \\frac{1}{N}\\sum_i (x_i - y_i)^2" },
        { kind: "p", text: ["La media debe alcanzar 38 dB. JPEG con calidad 85 es lo habitual. Guarda el color a media "
          + "resolución, algo invisible en la mayoría de los especímenes pero no en una lámina delgada entre "
          + "polarizadores cruzados, cuyos colores de interferencia son el detalle diagnóstico (32,1 dB en una lámina "
          + "delgada de Commons). Una imagen así se escribe de nuevo con calidad 90, donde libvips guarda el color a "
          + "resolución completa (49,9 dB)."] },
        { kind: "h3", text: "Teselas por IIIF" },
        { kind: "p", text: ["Los píxeles llegan al navegador mediante la ",
          { a: "IIIF Image API 3.0", href: "https://iiif.io/api/image/3.0/" },
          ", servida por iipsrv desde los archivos piramidales. Una solicitud nombra una región, un tamaño, una "
          + "rotación y una calidad:"] },
        { kind: "code", text: "/iiif/{identifier}/{region}/{size}/{rotation}/{quality}.jpg" },
        { kind: "p", text: ["Un visor de zoom profundo como OpenSeadragon pide solo teselas: una tesela de un nivel de la "
          + "pirámide. Cualquier visor IIIF puede abrir una lámina de Laminario mediante su manifiesto (la ",
          { a: "IIIF Presentation API 3.0", href: "https://iiif.io/api/presentation/3.0/" },
          "), y una tesela se sirve solo mientras su lámina está publicada."] },
        { kind: "h3", text: "El tamaño de píxel y los objetivos" },
        { kind: "p", text: ["Los escáneres combinan un objetivo con un tamaño de píxel cuyo producto se acerca a 10 "
          + "micrómetros (20x con 0,5 µm, 40x con 0,25 µm). Con el objetivo ", { m: "M" },
          " un píxel de pantalla cubre ", { m: "10/M" }, " µm, así una imagen cuyo píxel cubre ", { m: "p" },
          " µm se muestra a"] },
        { kind: "math", tex: "z = \\frac{p \\cdot M}{10}" },
        { kind: "p", text: ["píxeles de pantalla por píxel de imagen. La platina ofrece de 2x a 100x; un paso más allá "
          + "de la resolución propia de la imagen se rotula como zoom digital, y una imagen sin tamaño de píxel ofrece "
          + "solo zoom libre y dice que no está a escala. La barra de escala es la longitud mayor de la serie 1, 2, 5 "
          + "que cabe en un cuarto de la vista."] },
        { kind: "figure", figure: "objectives", caption: ["Una imagen con tres objetivos: el mismo píxel de 0,5 µm "
          + "dibujado sobre más píxeles de pantalla a medida que crece el objetivo; más allá de la resolución de la "
          + "imagen, el zoom es digital."] },
        { kind: "h3", text: "Pilas focales" },
        { kind: "p", text: ["Una pila focal muestra cada parte de un espécimen grueso nítida en un plano distinto. Hasta "
          + "500 MB, la pila se conserva completa; por encima, se conservan ", { m: "k = 11" }, " de sus ",
          { m: "n" }, " planos, espaciados de manera uniforme e incluidos ambos extremos:"] },
        { kind: "math", tex: "i_j = \\operatorname{round}\\left( j \\, \\frac{n - 1}{k - 1} \\right), \\qquad "
          + "j = 0, \\ldots, k-1" },
        { kind: "p", text: ["Cada plano conservado mantiene su índice y su profundidad originales, así la platina nombra "
          + "profundidades focales reales."] },
        { kind: "h3", text: "Todo enfocado" },
        { kind: "p", text: ["La profundidad de campo extendida construye una imagen nítida en todas partes y un mapa de "
          + "alturas: para cada píxel, el plano del que vino, que con las profundidades de los planos es un mapa de la "
          + "superficie del espécimen. Laminario sigue el complemento de la EPFL (Forster, Van De Ville, Berent, Sage "
          + "y Unser, 2004) con sus dos métodos. La selección por varianza toma, en cada píxel, el plano cuya vecindad "
          + "de 5 por 5 más varía:"] },
        { kind: "math", tex: "\\sigma_k^2(p) = \\sum_{q \\in N(p)} \\big(I_k(q) - \\mu_k(p)\\big)^2, \\qquad "
          + "h(p) = \\arg\\max_k \\sigma_k^2(p)" },
        { kind: "p", text: ["La fusión por ondículas complejas conserva, en cada coeficiente de una transformada de "
          + "ondículas complejas, el plano de mayor módulo, hace concordar las elecciones vecinas, invierte la "
          + "transformada y da a cada píxel el valor medido más cercano al resultado. En pilas cuyo foco real se "
          + "conoce, el mapa por varianza queda a un plano o menos de la verdad en el 99,9 por ciento de los píxeles; "
          + "la platina muestra la composición por ondículas y lee las profundidades del mapa por varianza."] },
        { kind: "p", text: ["Las comprobaciones de consistencia del complemento toman el alto de la imagen por su ancho, "
          + "lo que en una pila no cuadrada las lleva a regiones equivocadas. Laminario usa la geometría verdadera, "
          + "acertada tres veces más a menudo en pilas sintéticas no cuadradas, y conserva la convención del "
          + "complemento como opción, con la que su resultado es igual al del complemento en cada píxel."] },
        { kind: "figure", figure: "stack", caption: ["Una pila focal y lo que la fusión hace con ella: cada región nítida "
          + "en su propio plano, una composición nítida en todas partes y el mapa de alturas del plano del que vino "
          + "cada píxel."] },
        { kind: "h3", text: "Pares polarizados" },
        { kind: "p", text: ["Una lámina delgada de roca se fotografía dos veces en un mismo campo: con luz polarizada "
          + "plana y entre polarizadores cruzados, donde los minerales muestran sus colores de interferencia. La "
          + "platina abre ambas, funde una sobre la otra y gira la vista en cuartos de vuelta."] },
        { kind: "figure", figure: "polarised", caption: ["Un par polarizado: el polarizador bajo la lámina y, para los "
          + "polarizadores cruzados, el analizador sobre ella en ángulo recto."] },
        { kind: "h3", text: "Ninguna posición sale del servidor" },
        { kind: "p", text: ["Cada derivado conserva solo el perfil de color: sin EXIF, XMP ni IPTC, así ninguna posición "
          + "GPS que haya escrito una cámara. La posición de una fotografía se lee en el navegador antes de subirla y "
          + "se muestra a quien la aporta, que decide si el lugar es abierto, oculto o privado."] },
      ],
    },
    {
      id: "community", title: "La identificación", blocks: [
        { kind: "p", text: ["Quienes identifican dicen qué muestra una lámina, y el nombre en que más coinciden pasa a "
          + "ser el de la lámina. La regla es el ",
          { a: "taxón comunitario de iNaturalist", href: "https://github.com/inaturalist/inaturalist" },
          ", aplicado a todo tipo de ancla mediante su linaje. Para cada nodo ", { m: "t" }, ", con ",
          { m: "c(t)" }, " las identificaciones de ", { m: "t" }, " o de algo bajo él, ", { m: "d(t)" },
          " las que quedan fuera de su rama y ", { m: "a(t)" }, " los desacuerdos explícitos de un ancestro,"] },
        { kind: "math", tex: "\\mathrm{score}(t) = \\frac{c(t)}{c(t) + d(t) + a(t)}" },
        { kind: "p", text: ["El ancla comunitaria es el nodo más profundo con al menos dos identificaciones y una "
          + "puntuación mayor que dos tercios. Una lámina queda verificada cuando esa ancla es tan fina como su tipo "
          + "necesita, necesita identificación hasta entonces, y es lámina de referencia cuando falla una de sus "
          + "comprobaciones: todo escaneo base sin tamaño de píxel lo es, porque una lámina sin escala no permite "
          + "medir. Los curadores resuelven los avisos y pueden ocultar un elemento con una razón; cada ocultamiento y "
          + "cada restauración quedan registrados."] },
      ],
    },
    {
      id: "privacy", title: "Lo que nunca se muestra", blocks: [
        { kind: "list", items: [
          ["El correo de una cuenta. Los perfiles, las láminas y las identificaciones nombran a las personas por su "
            + "nombre visible y su identificador."],
          ["El lugar exacto de una lámina oculta. Su registro público da la celda de 0,2 grados en que se encuentra "
            + "(unos 22 km de sur a norte) y un punto fijo dentro de ella que depende solo de la celda y de la lámina, "
            + "nunca de dónde está el punto real, así dos respuestas no pueden combinarse para acotarlo."],
          ["Ningún lugar de una lámina privada más allá de su texto de localidad y su país."],
          ["Los metadatos de una cámara: cada derivado se escribe sin EXIF, XMP ni IPTC."],
        ] },
        { kind: "p", text: ["La exportación propia de quien aporta lleva los lugares exactos de sus láminas; la de nadie "
          + "más."] },
        { kind: "figure", figure: "geoprivacy", caption: ["Una lámina abierta en su punto; una oculta como su celda de "
          + "0,2 grados con un punto público dentro; una privada sin punto alguno."] },
      ],
    },
    {
      id: "names", title: "Los nombres detrás del árbol", blocks: [
        { kind: "p", text: ["El árbol ubica una lámina por el linaje de su ancla, y cada tipo de ancla tiene su "
          + "autoridad. Los nombres y la jerarquía del Rock Classification Scheme se usan como hechos; sus informes "
          + "se citan, no se copian."] },
        { kind: "live", what: "vocabularies" },
      ],
    },
    {
      id: "software", title: "Software, fuentes tipográficas y datos del mapa", blocks: [
        { kind: "p", text: ["Laminario está construido sobre software abierto, y cada pieza conserva su licencia. El "
          + "servidor de teselas (iipsrv) y las bibliotecas de imagen (libvips, OpenSlide) funcionan como programas "
          + "propios, sin modificar. Los íconos de la colección y los glifos de la interfaz están dibujados para "
          + "Laminario."] },
        { kind: "live", what: "software" },
        { kind: "live", what: "fonts" },
        { kind: "p", text: ["Los datos del mapa: © colaboradores de OpenStreetMap, bajo la Open Database License, de un "
          + "extracto de Protomaps. La esquina del mapa enlaza a ",
          { a: "la página de derechos de OpenStreetMap", href: "https://www.openstreetmap.org/copyright" }, "."] },
        { kind: "live", what: "map" },
      ],
    },
    {
      id: "references", title: "Referencias", blocks: [
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
    commons: ["Archivos de Wikimedia Commons, cada uno bajo la licencia que eligió su autor, leída de los metadatos del "
      + "propio archivo. El reconocimiento es el nombre del autor tal como lo da Commons, sin las plantillas de la "
      + "página del archivo."],
    nhm: ["Imágenes de especímenes del Portal de Datos del Natural History Museum de Londres: piojos y otros insectos "
      + "montados en lámina, fotografiados y escaneados por el museo, compartidos bajo CC BY 4.0, con The Trustees of "
      + "the Natural History Museum, London como titular de derechos."],
    smithsonian: ["Registros de Smithsonian Open Access, dedicados al dominio público (CC0), entre ellos los cristales "
      + "de nieve que Wilson Bentley fotografió a través de un microscopio, conservados por los Smithsonian "
      + "Institution Archives."],
    zenodo: ["Pilas focales de lámina completa del National Museum of Natural History del Smithsonian, publicadas en "
      + "Zenodo bajo CC BY 4.0, cada una con su DOI y sus autores."],
    openslide: ["Muestras de los datos de prueba de OpenSlide, CC0: cortes de ganglio linfático del conjunto de datos "
      + "CAMELYON16 (Computational Pathology Group, Radboud University Medical Center) y un frotis de médula ósea "
      + "escaneado por Maki Sakuma (National Center for Global Health and Medicine, doi:10.5061/dryad.6m905qfzx)."],
    contribution: ["Láminas aportadas por las personas de Laminario, cada imagen bajo la licencia que eligió quien la "
      + "aportó."],
    other: ["Imágenes cuya fuente esta página todavía no describe."],
  },
  licences: {
    cc0: { name: "CC0 1.0 (dedicación al dominio público)", text: ["Copiar, modificar, distribuir y comunicar la obra, "
      + "también con fines comerciales, sin pedir permiso. No se requiere reconocimiento; nombrar al autor y la "
      + "fuente es una cortesía."] },
    pdm: { name: "Marca de Dominio Público 1.0", text: ["Identificada como libre de restricciones de derechos de autor "
      + "conocidas: las mismas libertades que CC0, aunque la situación puede variar según el país."] },
    nkc: { name: "Sin Derechos de Autor Conocidos", text: ["La organización que la conserva cree que el elemento no "
      + "está restringido por derechos de autor, pero no pudo determinarlo de forma concluyente. Una declaración, no "
      + "una licencia."] },
    by: { name: "CC BY (Atribución)", text: ["Compartir y adaptar para cualquier fin, también comercial, dando el "
      + "reconocimiento adecuado, enlazando la licencia e indicando si hubo cambios."] },
    "by-sa": { name: "CC BY-SA (Atribución-CompartirIgual)", text: ["Como CC BY, y las adaptaciones deben compartirse "
      + "bajo la misma licencia."] },
    "by-nc": { name: "CC BY-NC (Atribución-NoComercial)", text: ["Compartir y adaptar con reconocimiento, pero no para "
      + "un uso cuyo fin principal sea una ventaja comercial o una compensación monetaria."] },
    "by-nc-sa": { name: "CC BY-NC-SA (Atribución-NoComercial-CompartirIgual)", text: ["Como CC BY-NC, y las "
      + "adaptaciones bajo la misma licencia."] },
  },
  figures: {
    pyramid: { level: "Nivel", tile: "tesela de 512 px", full: "resolución completa",
      half: "cada nivel, la mitad del de arriba", title: "Los niveles de una pirámide en teselas" },
    objectives: { screen: "píxeles de pantalla por píxel de imagen", digital: "zoom digital",
      image: "píxel de imagen, 0,5 µm", title: "Una imagen con tres objetivos" },
    stack: { planes: "planos focales", composite: "todo enfocado", height: "mapa de alturas",
      title: "Una pila focal fusionada" },
    polarised: { light: "luz", polariser: "polarizador", section: "lámina delgada", analyser: "analizador",
      ppl: "luz polarizada plana", xpl: "polarizadores cruzados", title: "Un par polarizado" },
    geoprivacy: { open: "abierta: el punto", obscured: "oculta: la celda de 0,2 grados, un punto público",
      private: "privada: sin punto", title: "Geoprivacidad" },
  },
  live: {
    slides: "Láminas publicadas", base: "de la colección base", contribution: "aportadas", wsi: "escaneos de lámina "
      + "completa", images: "imágenes", countries: "países", contributors: "personas que aportan",
    identifications: "identificaciones de la comunidad", realm: "Reino", collections: "colecciones", source: "Fuente",
    images_col: "Imágenes", slides_col: "Láminas", licences_col: "Licencias", licence: "Licencia",
    allows: "Qué permite", read: "Contada el", name: "Nombre", citation: "Cita", licence_col: "Licencia",
    none: "citada", software: "Software", fonts: "Fuentes tipográficas", map: "Datos del mapa",
    failed: "No se pudieron leer las cifras. Intente de nuevo en un momento.", terms: "condiciones",
    contributions: "Aportes", others: "Otras fuentes",
  },
};
