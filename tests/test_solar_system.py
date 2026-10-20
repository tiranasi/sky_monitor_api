from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import astronomy as sky, main


def test_missing_ephemeris_is_a_service_error(monkeypatch, tmp_path):
    monkeypatch.setattr(sky, "DATA_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="ephemeris"):
        sky.solar_system_positions(31.3, 120.6)
    monkeypatch.setattr(main, "build_sky_chart", lambda **kwargs: sky.solar_system_positions(31.3, 120.6))
    with TestClient(main.app) as client:
        assert client.get("/sky/chart", params={"lat": 31.3, "lon": 120.6}).status_code == 503
        assert client.post("/sky/chart", json={"lat": 31.3, "lon": 120.6}).status_code == 503


def test_corrupt_ephemeris_is_not_an_empty_success(monkeypatch, tmp_path):
    (tmp_path / "de421.bsp").write_bytes(b"invalid kernel")
    monkeypatch.setattr(sky, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sky, "_SKYFIELD_EPHEMERIS", None)
    with pytest.raises(sky.SolarSystemUnavailableError):
        sky.solar_system_positions(31.3, 120.6)


@pytest.fixture
def ephemeris():
    if not (sky.DATA_DIR / "de421.bsp").exists():
        pytest.skip("Install data/de421.bsp to run JPL position regression checks")


def test_suzhou_sun_moon_and_saturn_positions(ephemeris):
    rows = sky.solar_system_positions(31.2989, 120.5853, "2026-10-20T12:00:00Z")
    assert len(rows) == 7
    by_category = {item["category"]: item for item in rows if item["category"] != "planet"}
    # Fixed-date JPL DE421 results, Sun/Moon independently cross-checked with Astropy.
    assert by_category["sun"]["azimuth_deg"] == pytest.approx(279.35, abs=.02)
    assert by_category["sun"]["altitude_deg"] == pytest.approx(-34.67, abs=.02)
    assert by_category["moon"]["azimuth_deg"] == pytest.approx(192.16, abs=.02)
    assert by_category["moon"]["altitude_deg"] == pytest.approx(40.58, abs=.02)
    assert by_category["moon"]["distance_au"] == pytest.approx(.00262450, abs=.00000001)
    saturn = next(item for item in rows if "Saturn" in item["name"])
    assert saturn["altitude_deg"] == pytest.approx(41.34, abs=.02)
    planets = sky.planet_positions(31.2989, 120.5853, "2026-10-20T12:00:00Z")
    assert len(planets) == 5
    assert all(set(item) == {"name", "azimuth_deg", "altitude_deg", "distance_au"} for item in planets)


def test_out_of_range_time_is_rejected(ephemeris):
    with pytest.raises(ValueError, match="date range"):
        sky.solar_system_positions(31.3, 120.6, "2060-10-20T12:00:00Z")


def test_facts_visible_planets_exclude_below_horizon(monkeypatch):
    monkeypatch.setattr(sky, "visible_stars", lambda **kwargs: [])
    monkeypatch.setattr(sky, "planet_positions", lambda *args:
                        [{"name": "above", "altitude_deg": 20}, {"name": "below", "altitude_deg": -20}])
    assert [row["name"] for row in sky.build_answer_facts(31.3, 120.6)["visible_planets"]] == ["above"]


def test_chart_contains_luminaries_and_switch_disables_all_solar_objects(monkeypatch):
    monkeypatch.setattr(sky, "visible_stars", lambda **kwargs: [])
    monkeypatch.setattr(sky, "visible_deep_sky_objects", lambda **kwargs: [])
    monkeypatch.setattr(sky, "solar_system_positions", lambda *args: [
        {"name": "Moon / 月亮", "category": "moon", "azimuth_deg": 90, "altitude_deg": 30},
        {"name": "Sun / 太阳", "category": "sun", "azimuth_deg": 180, "altitude_deg": 45},
        {"name": "below", "category": "planet", "azimuth_deg": 20, "altitude_deg": -20},
    ])
    chart = sky.build_sky_chart(31.3, 120.6)
    assert chart["counts"] == {"sun": 1, "moon": 1}
    assert "Sun" not in chart["reasoning_context"]["summary"]
    sun = next(item for item in chart["reasoning_context"]["object_insights"] if item["category"] == "sun")
    assert "请勿直视" in sun["viewing_tip"]
    assert sun["altitude_note"] == sun["magnitude_note"] == ""
    assert sky.build_sky_chart(31.3, 120.6, include_planets=False)["objects"] == []
