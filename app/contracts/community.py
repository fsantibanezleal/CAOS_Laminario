"""What an identifier, a flagger or a curator sends (U13).

An identification names an anchor as a submission does (``Anchor``), with an optional comment, and, when it names an
ancestor of the slide's anchor, whether it disagrees with the finer one (R-1302). A flag names its target, a category
and a comment; a curator's hiding or restoring carries its reason (R-1306).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.ingest import Anchor


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class IdentificationIn(_In):
    anchor: Anchor
    body: str | None = Field(None, max_length=1000)
    disagreement: bool | None = None


class VoteIn(_In):
    #: True: the community anchor is as good as it can be; False: it still needs identification; None: no vote.
    as_good_as_it_can_be: bool | None = None


TargetKind = Literal["slide", "identification", "annotation"]


class FlagIn(_In):
    target_kind: TargetKind
    target_id: str = Field(min_length=1, max_length=32)
    category: Literal["spam", "inappropriate", "copyright", "wrong", "other"]
    comment: str | None = Field(None, max_length=1000)


class ResolveIn(_In):
    resolution: str = Field(min_length=1, max_length=1000)


class ReasonIn(_In):
    #: As iNaturalist asks of its curators: at least 10 characters.
    reason: str = Field(min_length=10, max_length=2000)
