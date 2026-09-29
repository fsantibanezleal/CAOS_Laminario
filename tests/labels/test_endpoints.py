"""The slide object and its print sheet over HTTP: a published slide's, and nothing for any other id."""

from __future__ import annotations

from tests.accounts.support import app_client, settings_for
from tests.explore.test_explore import seed


def test_slide_svg_and_label_pdf(tmp_path):
    settings = settings_for(tmp_path)
    [sid] = seed(settings, [{"preparation": "smear"}])
    with app_client(settings) as client:
        drawn = client.get(f"/api/slides/{sid}/slide.svg")
        assert drawn.status_code == 200 and drawn.headers["content-type"].startswith("image/svg+xml")
        assert f'data-slide="{sid}"' in drawn.text and "<style>" in drawn.text and 'class="lam-qr"' in drawn.text
        inline = client.get(f"/api/slides/{sid.lower()}/slide.svg", params={"standalone": "false", "lang": "es"})
        assert inline.status_code == 200 and "<style>" not in inline.text and "Frotis" in inline.text
        sheet = client.get(f"/api/slides/{sid}/label.pdf")
        assert sheet.status_code == 200 and sheet.content.startswith(b"%PDF")
        assert sheet.headers["content-disposition"] == f'inline; filename="laminario-{sid}.pdf"'
        assert client.get("/api/slides/ZZZZZZZZ/slide.svg").status_code == 404
        assert client.get("/api/slides/ZZZZZZZZ/label.pdf").status_code == 404
        assert client.get(f"/api/slides/{sid}/slide.svg", params={"lang": "fr"}).status_code == 422
