from __future__ import annotations

import math
import json

from app.deep_sky import CATALOG_PATH, get_deep_sky_objects
from scripts.build_deep_sky_catalog import build_catalog, ROOT


def test_complete_messier_catalog_and_existing_extras():
    rows = get_deep_sky_objects()
    assert len(rows) == len({row["id"] for row in rows}) == 114
    assert {row["id"] for row in rows if row["id"].startswith("M")} == {f"M{i}" for i in range(1, 111)}
    assert {row["id"] for row in rows if not row["id"].startswith("M")} == {
        "NGC 869/884", "NGC 5139", "NGC 104", "NGC 3372"}
    for row in rows:
        assert math.isfinite(row["ra_deg"]) and 0 <= row["ra_deg"] < 360
        assert math.isfinite(row["dec_deg"]) and -90 <= row["dec_deg"] <= 90
        assert row["magnitude"] is None or math.isfinite(row["magnitude"])
        assert row["name_en"] and row["object_type"] and row["constellation"]


def test_special_identifications_and_missing_photometry():
    rows = {row["id"]: row for row in get_deep_sky_objects()}
    assert rows["M40"]["object_type"] == "double_star"
    assert rows["M73"]["object_type"] == "asterism"
    assert rows["M45"]["object_type"] == "open_cluster"
    assert rows["M102"]["constellation"] == "Dra"
    assert rows["M102"]["ra_deg"] != rows["M101"]["ra_deg"]
    assert rows["M35"]["magnitude"] == 5.3
    assert rows["M107"]["magnitude"] == 8.9
    assert rows["M31"]["name_zh"] == "仙女座大星系"


def test_catalog_results_do_not_mutate_cached_data():
    rows = get_deep_sky_objects()
    rows[0]["id"] = "changed"
    assert get_deep_sky_objects()[0]["id"] == "M1"


def test_build_pinned_sources_reproduces_catalog(tmp_path):
    import pytest
    source_dir = ROOT / "data/raw/openngc"
    if not (source_dir / "NGC.csv").exists():
        pytest.skip("Download pinned OpenNGC sources to check full regeneration")
    output = tmp_path / "catalog.json"
    build_catalog(source_dir, ROOT / "data/deep_sky_overrides.json", output)
    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
