"""The IIIF best-fit size never asks iipsrv for more than the image holds.

iipsrv 1.3 answers 400 to ``!w,h`` whenever ``w`` or ``h`` exceeds the image's own side, though a best fit only
shrinks; the glass view's ``!1024,1024`` failed for 95 of the 505 base slides.
"""

from __future__ import annotations

from app.delivery.iiif import best_fit


def test_a_box_larger_than_a_side_is_capped_at_that_side():
    # the slide the review found: a 1280x720 image
    assert best_fit(1024, 1280, 720) == "!1024,720"
    assert best_fit(800, 1280, 720) == "!800,720"


def test_a_box_inside_the_image_is_unchanged():
    assert best_fit(320, 1280, 720) == "!320,320"


def test_a_small_image_is_asked_for_at_its_own_size():
    assert best_fit(1024, 640, 480) == "!640,480"


def test_an_unknown_size_sends_the_plain_box():
    assert best_fit(320, None, None) == "!320,320"
    assert best_fit(320, 1280, None) == "!320,320"
