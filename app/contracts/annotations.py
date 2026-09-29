"""What an annotation's author sends: the W3C Web Annotation's bodies and its selector (R-1108).

The rest of the annotation is the server's: its id, its target source (the asset's own image, whatever the client
sent), its creator and its dates. Bodies are text; a selector is a rectangle in the image's pixels (a Media Fragments
``xywh=pixel:`` value) or a polygon (an SVG ``polygon`` with numeric points and nothing else), so no markup can be
stored and drawn back to another visitor.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MEDIA_FRAGMENTS = "http://www.w3.org/TR/media-frags/"
XYWH = re.compile(r"^xywh=pixel:(\d+(?:\.\d+)?),(\d+(?:\.\d+)?),(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)$")
POLYGON = re.compile(r'^<svg(?: xmlns="http://www\.w3\.org/2000/svg")?>\s*<polygon points="([0-9., ]{7,20000})"\s*'
                     r"(?:/>|></polygon>)\s*</svg>$")


class TextualBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["TextualBody"] = "TextualBody"
    value: str = Field(min_length=1, max_length=2000)
    purpose: Literal["commenting", "describing", "tagging", "identifying"] = "commenting"
    format: Literal["text/plain"] = "text/plain"
    language: Literal["en", "es"] | None = None


class FragmentSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["FragmentSelector"]
    conformsTo: Literal["http://www.w3.org/TR/media-frags/"] = MEDIA_FRAGMENTS
    value: str = Field(max_length=100)

    @field_validator("value")
    @classmethod
    def _rectangle(cls, value: str) -> str:
        match = XYWH.match(value)
        if not match or float(match.group(3)) <= 0 or float(match.group(4)) <= 0:
            raise ValueError("a rectangle in pixels: xywh=pixel:x,y,w,h with a positive width and height")
        return value


class SvgSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["SvgSelector"]
    value: str = Field(max_length=20100)

    @field_validator("value")
    @classmethod
    def _polygon(cls, value: str) -> str:
        match = POLYGON.match(value.strip())
        if not match:
            raise ValueError("an SVG with one polygon of numeric points and nothing else")
        numbers = re.split(r"[ ,]+", match.group(1).strip())
        if len(numbers) < 6 or len(numbers) % 2:
            raise ValueError("a polygon needs at least three points, each an x and a y")
        return value.strip()


class AnnotationTarget(BaseModel):
    model_config = ConfigDict(extra="ignore")  # the source is the server's: whatever the client sent is ignored

    selector: FragmentSelector | SvgSelector = Field(discriminator="type")


class AnnotationIn(BaseModel):
    """A new annotation, or the new content of one: its bodies and where on the image it points."""

    model_config = ConfigDict(extra="ignore")  # @context, id, type, creator and dates are the server's

    body: list[TextualBody] = Field(default_factory=list, max_length=10)
    target: AnnotationTarget
