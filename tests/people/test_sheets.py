"""R-1404 to R-1406 over HTTP: the stocks, a sheet of labels for published slides, and a stock's test page."""

from __future__ import annotations

from app.labels import sheet
from app.labels.stocks import stocks
from tests.accounts.support import app_client, settings_for
from tests.community.support import people, published


def test_stocks_and_sheets(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        listed = client.get("/api/labels/stocks").json()
        assert [s["id"] for s in listed] == list(stocks())
        plain = next(s for s in listed if s["id"] == "a4-plain")
        assert plain["per_sheet"] == 72 and plain["kind"] == "plain" and plain["warnings"] == ["plain_paper"]

        p = people(client, settings)
        sids = [published(client, settings, p["maker"]) for _ in range(2)]
        url = "/api/labels/sheet.pdf"
        answer = client.get(url, params={"stock": "a4-plain", "slides": ",".join(sids), "start": 5, "dx": 0.5,
                                         "dy": -0.5, "lang": "es"})
        assert answer.status_code == 200, answer.text
        assert answer.headers["content-type"] == "application/pdf" and answer.content.startswith(b"%PDF")
        # The scanned id is forgiven its case, as on the slide place.
        assert client.get(url, params={"stock": "a4-plain", "slides": sids[0].lower()}).status_code == 200

        test = client.get(url, params={"stock": "divbio-misl-1000", "test": "true"})
        assert test.status_code == 200 and test.content.startswith(b"%PDF")
        assert 'filename="laminario-test-divbio-misl-1000.pdf"' in test.headers["content-disposition"]

        assert client.get(url, params={"stock": "no-such", "slides": sids[0]}).status_code == 404
        assert client.get(url, params={"stock": "a4-plain"}).status_code == 422
        assert client.get(url, params={"stock": "a4-plain", "slides": "ZZZZZZZZ"}).status_code == 404
        assert client.get(url, params={"stock": "a4-plain", "slides": sids[0], "start": 72}).status_code == 422
        assert client.get(url, params={"stock": "a4-plain", "slides": sids[0], "dx": 11}).status_code == 422
        too_many = ",".join([sids[0]] * (sheet.MAX_SLIDES + 1))
        assert client.get(url, params={"stock": "a4-plain", "slides": too_many}).status_code == 422
