from __future__ import annotations

from app.main import SkyChartRequest, SkyFactsRequest
from app import main
from fastapi.testclient import TestClient
import pytest


def test_sky_chart_request_accepts_gps_aliases() -> None:
    payload = SkyChartRequest(
        latitude=31.2304,
        longitude=121.4737,
        max_magnitude=3.0,
        total_limit=8,
    )

    assert payload.lat == 31.2304
    assert payload.lon == 121.4737
    assert payload.star_max_mag == 3.0


def test_sky_facts_request_accepts_gps_aliases() -> None:
    payload = SkyFactsRequest(
        latitude=31.2304,
        longitude=121.4737,
        max_magnitude=3.0,
    )

    assert payload.lat == 31.2304
    assert payload.lon == 121.4737
    assert payload.max_mag == 3.0


def test_chart_get_and_post_share_limit_and_aliases(monkeypatch) -> None:
    monkeypatch.setattr(main, "build_sky_chart", lambda **kwargs: kwargs)
    with TestClient(main.app) as client:
        payload = {"latitude": 31.3, "longitude": 120.6, "total_limit": 150, "max_magnitude": 5.0}
        get = client.get("/sky/chart", params=payload)
        post = client.post("/sky/chart", json=payload)
        assert get.status_code == post.status_code == 200
        assert get.json() == post.json()
        assert get.json()["sky_chart"]["total_limit"] == 150
        payload["star_max_mag"] = 2.0
        assert client.get("/sky/chart", params=payload).json() == client.post("/sky/chart", json=payload).json()


@pytest.mark.parametrize("limit", [7, 151])
def test_chart_rejects_out_of_range_limit_in_both_methods(limit) -> None:
    with TestClient(main.app) as client:
        payload = {"lat": 31.3, "lon": 120.6, "total_limit": limit}
        assert client.get("/sky/chart", params=payload).status_code == 422
        assert client.post("/sky/chart", json=payload).status_code == 422
