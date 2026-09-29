"""IIIF Presentation 3 manifests: a slide as a document any IIIF viewer opens.

Built from the catalog record (so geoprivacy is already applied), never from rows and never with a network
call. One Canvas per ready micro asset (each focal plane and each polarisation state is its own asset) and per
ready macro asset, in the slide's asset order. Every Canvas carries its own ``rights`` and
``requiredStatement``, because the images of one slide can carry different licences; the Manifest carries
``rights`` only when all of them agree.

- Local pyramids are painted as images with an ``ImageService3`` (level 2) at this deployment's ``/iiif``.
- Remote IIIF assets keep their institution's service, declared with the Image API version recorded when the
  remote-asset contract was checked.
- Plain images (macro photographs) are painted directly.

``partOf`` names the slide's collection node as a IIIF Collection; ``navPlace`` (the IIIF extension) carries
the public place: the point for an open place, the 0.2 degree cell for an obscured one, nothing for a
private one.
"""

from __future__ import annotations

from app.contracts import catalog as c
from app.contracts import licences

PRESENTATION_CONTEXT = "http://iiif.io/api/presentation/3/context.json"
NAVPLACE_CONTEXT = "http://iiif.io/api/extension/navplace/context.json"
MANIFEST_MEDIA_TYPE = f'application/ld+json;profile="{PRESENTATION_CONTEXT}"'
PRODUCT_NAME = "Laminario"
#: Assets that are data for the interface, not images to look at (the height map feeds the depth readout).
NOT_PAINTED = ("height_map",)

IMAGE_FORMATS = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp",
                 "tif": "image/tiff", "tiff": "image/tiff"}


def _text(value: str, language: str = "en") -> dict:
    return {language: [value]}


def _entry(label: str, value: str | None, language: str = "none") -> dict | None:
    if value is None or value == "":
        return None
    return {"label": _text(label), "value": _text(str(value), language)}


def collection_url(base: str, node: str) -> str:
    """The IIIF Collection of a collection node (served by the collection tree, U7)."""
    return f"{base}/api/collections/{node}/iiif"


def asset_label(asset: c.AssetRecord) -> str:
    parts = [asset.caption] if asset.caption else [f"{asset.family} {asset.role}".replace("_", " ")]
    if asset.plane:
        parts.append(f"focal plane {asset.plane.index} at {asset.plane.depth_um:g} um")
    if asset.polarisation:
        state = "plane-polarised" if asset.polarisation.state == "ppl" else "crossed polars"
        parts.append(f"{state}, {asset.polarisation.angle_deg:g} deg")
    if asset.modality:
        parts.append(asset.modality.replace("_", " "))
    return ", ".join(parts)


def attribution(asset: c.AssetRecord) -> str:
    who = asset.creator or asset.rights_holder
    text = f"{who}, {asset.licence.short_name}" if who else asset.licence.short_name
    if asset.rights_holder and asset.creator and asset.rights_holder != asset.creator:
        text += f" (rights holder: {asset.rights_holder})"
    if asset.source:
        text += f"; source: {asset.source.url}"
    return text


def _service(asset: c.AssetRecord) -> dict | None:
    info = asset.media.iiif_info_url
    if not info:
        return None
    service = info.removesuffix("/info.json")
    if asset.media.iiif_version == 2:
        return {"@id": service, "@type": "ImageService2", "profile": "http://iiif.io/api/image/2/level2.json"}
    return {"id": service, "type": "ImageService3", "profile": "level2"}


def _body(asset: c.AssetRecord) -> dict:
    width, height = asset.media.width_px, asset.media.height_px
    service = _service(asset)
    if service is not None:
        base = service.get("id") or service["@id"]
        body = {"id": f"{base}/full/max/0/default.jpg", "type": "Image", "format": "image/jpeg",
                "service": [service]}
    else:
        url = asset.media.image_url or ""
        extension = url.rsplit(".", 1)[-1].lower() if "." in url else ""
        body = {"id": url, "type": "Image", "format": IMAGE_FORMATS.get(extension, "image/jpeg")}
    if width and height:
        body |= {"width": width, "height": height}
    return body


def canvas(manifest_id: str, asset: c.AssetRecord) -> dict:
    canvas_id = f"{manifest_id}/canvas/{asset.id}"
    rights = licences.iiif_rights(asset.licence.uri)
    result = {
        "id": canvas_id,
        "type": "Canvas",
        "label": _text(asset_label(asset)),
        "width": asset.media.width_px,
        "height": asset.media.height_px,
        "requiredStatement": {"label": _text("Attribution"), "value": _text(attribution(asset))},
        "items": [{
            "id": f"{canvas_id}/page",
            "type": "AnnotationPage",
            "items": [{
                "id": f"{canvas_id}/page/image",
                "type": "Annotation",
                "motivation": "painting",
                "body": _body(asset),
                "target": canvas_id,
            }],
        }],
    }
    if rights:
        result["rights"] = rights
    metadata = [m for m in (
        _entry("Licence", asset.licence.short_name),
        _entry("Pixel size", f"{asset.pixel_size_um:g} um" if asset.pixel_size_um else None),
        _entry("Source record", asset.source.url if asset.source else None),
    ) if m]
    if metadata:
        result["metadata"] = metadata
    return result


def _nav_place(slide: c.SlideRecord, manifest_id: str) -> dict | None:
    place = slide.place
    if place.geoprivacy == "private" or place.point is None:
        return None
    if place.geoprivacy == "obscured" and place.cell is not None:
        cell = place.cell
        geometry = {"type": "Polygon", "coordinates": [[
            [cell.west, cell.south], [cell.east, cell.south], [cell.east, cell.north],
            [cell.west, cell.north], [cell.west, cell.south],
        ]]}
        label = "collection place, generalised to a 0.2 degree cell"
    else:
        geometry = {"type": "Point", "coordinates": [place.point.lon, place.point.lat]}
        label = "collection place"
    return {
        "id": f"{manifest_id}/place",
        "type": "FeatureCollection",
        "features": [{"id": f"{manifest_id}/place/1", "type": "Feature",
                      "properties": {"label": _text(label)}, "geometry": geometry}],
    }


def manifest(slide: c.SlideRecord, public_base_url: str) -> dict:
    """The IIIF Presentation 3 Manifest of a slide."""
    base = public_base_url.rstrip("/")
    manifest_id = slide.manifest_url
    ready = [a for a in slide.assets if a.status == "ready" and a.media.width_px and a.media.height_px
             and a.role not in NOT_PAINTED]
    ordered = sorted(ready, key=lambda a: (0 if a.family == "micro" else 1, a.sort_order, a.id))
    label = slide.label
    anchor = slide.anchor
    metadata = [m for m in (
        _entry("Name", anchor.name),
        _entry("Rank", anchor.rank),
        _entry("Kind", anchor.kind),
        _entry("Collection", slide.placement.node),
        _entry("Preparation", label.preparation),
        _entry("Stain", label.stain),
        _entry("Mountant", label.mountant),
        _entry("Prepared", " by ".join(str(v) for v in (label.prepared_on, label.preparer) if v) or None),
        _entry("Collected", " by ".join(str(v) for v in (label.collected_on, label.collector) if v) or None),
        _entry("Locality", slide.place.locality_text if slide.place.geoprivacy != "private" else None),
        _entry("Type status", label.type_status),
        _entry("Catalogue number", label.catalogue_number),
        _entry("Slide", f"{slide.format.width_mm:g} x {slide.format.height_mm:g} mm"),
        _entry("Quality", slide.quality.badge.replace("_", " ")),
        _entry("Origin", "base collection" if slide.origin == "base" else "contribution"),
    ) if m]
    rights = {licences.iiif_rights(a.licence.uri) for a in ordered}
    statements = sorted({attribution(a) for a in ordered})
    document = {
        "@context": [NAVPLACE_CONTEXT, PRESENTATION_CONTEXT],
        "id": manifest_id,
        "type": "Manifest",
        "label": _text(anchor.name, "none"),
        "summary": _text(f"{anchor.name}, {label.preparation or 'microscope slide'}, {slide.id}"),
        "metadata": metadata,
        "requiredStatement": {"label": _text("Attribution"),
                              "value": _text("; ".join(statements) if statements else PRODUCT_NAME)},
        "homepage": [{"id": slide.permalink, "type": "Text", "label": _text(f"{anchor.name} on {PRODUCT_NAME}"),
                      "format": "text/html"}],
        "seeAlso": [{"id": f"{base}/api/slides/{slide.id}", "type": "Dataset", "format": "application/json",
                     "profile": f"{base}/contracts/catalog.schema.json"}],
        "partOf": [{"id": collection_url(base, slide.placement.node), "type": "Collection"}],
        "provider": [{"id": f"{base}/about", "type": "Agent", "label": _text(PRODUCT_NAME),
                      "homepage": [{"id": f"{base}/", "type": "Text", "label": _text(PRODUCT_NAME),
                                    "format": "text/html"}]}],
        "items": [canvas(manifest_id, a) for a in ordered],
    }
    if len(rights) == 1 and None not in rights:
        document["rights"] = rights.pop()
    first_service = next((_service(a) for a in ordered if _service(a)), None)
    if first_service:
        service_base = first_service.get("id") or first_service["@id"]
        document["thumbnail"] = [{"id": f"{service_base}/full/!320,320/0/default.jpg", "type": "Image",
                                  "format": "image/jpeg", "service": [first_service]}]
    place = _nav_place(slide, manifest_id)
    if place:
        document["navPlace"] = place
    return document
