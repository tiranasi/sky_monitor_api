"""Offline end-to-end checks using the installed HYG database and JPL kernel."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import astronomy as sky, main
from app.db import resolve_db_path


@pytest.fixture
def client():
    if not resolve_db_path().exists() or not (sky.DATA_DIR / "de421.bsp").exists():
        pytest.skip("Build catalog.db and install de421.bsp for full chart integration checks")
    with TestClient(main.app) as client:
        yield client


@pytest.mark.parametrize("lat,lon,time", [
    (31.2989, 120.5853, "2026-10-20T12:00:00Z"),
    (31.2989, 120.5853, "2026-10-20T04:00:00Z"),
    (51.5074, -.1278, "2026-01-01T22:00:00Z"),
    (-33.8688, 151.2093, "2026-06-01T12:00:00Z"),
])
def test_real_chart_methods_preserve_contract_and_fill_budget(client, lat, lon, time):
    payload = {"lat": lat, "lon": lon, "time_utc": time, "total_limit": 150,
               "star_max_mag": 6, "deep_sky_max_mag": 12, "min_altitude_deg": 15}
    get = client.get("/sky/chart", params=payload)
    post = client.post("/sky/chart", json=payload)
    assert get.status_code == post.status_code == 200
    assert get.json() == post.json()
    assert set(get.json()) == {"sky_chart"}
    chart = get.json()["sky_chart"]
    assert set(chart) == {"observer", "time_utc", "coordinate_system", "constraints", "counts", "objects", "reasoning_context"}
    assert len(chart["objects"]) == sum(chart["counts"].values()) == 150
    assert chart["counts"]["star"] > 14 and chart["counts"]["deep_sky"] > 12
    assert len({row["id"] for row in chart["objects"]}) == 150
    allowed_fields = {"id", "category", "object_type", "name_en", "name_zh", "display_name",
                      "ra_deg", "dec_deg", "azimuth_deg", "altitude_deg", "magnitude", "constellation",
                      "chart_x", "chart_y", "chart_radius", "zenith_distance_deg", "label_priority",
                      "selection_reason", "distance_ly", "distance_au", "spectral_type"}
    for row in chart["objects"]:
        assert set(row) <= allowed_fields
        minimum = 15 if row["category"] in ("star", "deep_sky") else 0
        assert minimum <= row["altitude_deg"] <= 90
        assert 0 <= row["azimuth_deg"] < 360


def test_real_chart_keeps_bright_stars_and_returns_moon(client):
    payload = {"lat": 31.2989, "lon": 120.5853, "time_utc": "2026-10-20T12:00:00Z", "total_limit": 150}
    bright = client.get("/sky/chart", params={**payload, "star_max_mag": 3}).json()["sky_chart"]
    expanded = client.get("/sky/chart", params={**payload, "star_max_mag": 6}).json()["sky_chart"]
    expanded_stars = {row["id"] for row in expanded["objects"] if row["category"] == "star"}
    assert {row["id"] for row in bright["objects"] if row["category"] == "star"} <= expanded_stars
    assert {"Vega", "Altair"} <= expanded_stars
    assert expanded["counts"]["moon"] == 1
    assert expanded["counts"]["planet"] == 1
    assert expanded["counts"].get("sun", 0) == 0


def test_real_chart_solar_switch_and_invalid_date(client):
    payload = {"lat": 31.2989, "lon": 120.5853, "time_utc": "2026-10-20T04:00:00Z"}
    day = client.get("/sky/chart", params=payload).json()["sky_chart"]
    assert day["counts"]["sun"] == 1
    disabled = client.post("/sky/chart", json={**payload, "include_planets": False}).json()["sky_chart"]
    assert all(row["category"] not in ("planet", "sun", "moon") for row in disabled["objects"])
    invalid = {**payload, "time_utc": "2060-01-01T00:00:00Z"}
    assert client.get("/sky/chart", params=invalid).status_code == 400
    assert client.post("/sky/chart", json=invalid).status_code == 400
