from __future__ import annotations

from collections import Counter

import pytest

from app import astronomy as sky


def star(index: int, magnitude: float = 4.0, altitude: float = 60.0) -> dict:
    return {"name_en": f"HIP {index}", "ra_deg": float(index % 360), "dec_deg": 20.0,
            "magnitude": magnitude, "test_altitude": altitude}


def deep(index: int, magnitude: float = 8.0) -> dict:
    return {"id": f"M{index}", "name_en": f"DSO {index}", "object_type": "galaxy",
            "ra_deg": float(index), "dec_deg": 20.0, "magnitude": magnitude, "importance": 1}


@pytest.fixture
def positioned(monkeypatch):
    monkeypatch.setattr(sky, "_bulk_altaz_from_stars", lambda rows, *args:
                        [(90.0, row.get("test_altitude", 60.0)) for row in rows])
    monkeypatch.setattr(sky, "planet_positions", lambda *args: [])


def test_bright_low_star_survives_expanding_magnitude_limit(monkeypatch, positioned):
    rows = [star(1, 0.03, 25.0)] + [star(i, 5.0, 85.0) for i in range(2, 202)]
    monkeypatch.setattr(sky, "get_candidate_stars_for_sky", lambda **kwargs: rows)
    bright = sky.visible_stars(31.3, 120.6, max_mag=3, limit=60)
    expanded = sky.visible_stars(31.3, 120.6, max_mag=6, limit=60)
    assert bright[0]["name_en"] == expanded[0]["name_en"] == "HIP 1"
    assert len(expanded) == 60


def test_chart_reaches_150_and_reserves_each_category(monkeypatch, positioned):
    monkeypatch.setattr(sky, "get_candidate_stars_for_sky", lambda **kwargs:
                        [star(i) for i in range(250)])
    monkeypatch.setattr(sky, "get_deep_sky_objects", lambda: [deep(i) for i in range(1, 111)])
    monkeypatch.setattr(sky, "planet_positions", lambda *args:
                        [{"name": f"Planet {i}", "azimuth_deg": 90., "altitude_deg": 60.} for i in range(5)])
    chart = sky.build_sky_chart(31.3, 120.6, star_max_mag=6, total_limit=150)
    assert len(chart["objects"]) == 150
    assert chart["counts"] == {"planet": 5, "star": 97, "deep_sky": 48}
    assert Counter(item["category"] for item in chart["objects"]) == chart["counts"]
    assert len({item["id"] for item in chart["objects"]}) == 150


@pytest.mark.parametrize("stars,dsos,expected", [(200, 3, (147, 3)), (3, 200, (3, 147)), (3, 2, (3, 2))])
def test_category_budget_backfills_without_inventing_targets(stars, dsos, expected):
    selected = sky._select_chart_objects([{"category": "star"} for _ in range(stars)],
                                        [{"category": "deep_sky"} for _ in range(dsos)], [], 150)
    counts = Counter(item["category"] for item in selected)
    assert (counts["star"], counts["deep_sky"]) == expected


def test_famous_deep_sky_still_obeys_magnitude_cutoff(monkeypatch, positioned):
    monkeypatch.setattr(sky, "get_deep_sky_objects", lambda: [deep(1, 3), deep(2, 10), deep(3, None)])
    assert sky.visible_deep_sky_objects(31.3, 120.6, max_mag=0, limit=150) == []
    assert [row["id"] for row in sky.visible_deep_sky_objects(31.3, 120.6, max_mag=9)] == ["M1"]


def test_height_filter_is_applied_before_selection(monkeypatch, positioned):
    monkeypatch.setattr(sky, "get_candidate_stars_for_sky", lambda **kwargs:
                        [star(1, -1, -10), star(2, 1, 30)])
    assert [row["name_en"] for row in sky.visible_stars(31.3, 120.6)] == ["HIP 2"]
