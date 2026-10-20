"""Build the small, offline Messier catalogue from a pinned OpenNGC snapshot."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENNGC_REVISION = "be3cd6c5498806a2fbb2f7e0452ef802dbb02be0"
SOURCE_HASHES = {
    "NGC.csv": "54abea0b57b0a103831bfc7a8e3a99a23acfbf4bb581fcf3d8af539cbb826c84",
    "addendum.csv": "c93f983dda6780b76b7b2e9271a856a892627710148a982ee98101a54c642fdd",
}
TYPES = {
    "G": "galaxy", "OCl": "open_cluster", "GCl": "globular_cluster",
    "PN": "planetary_nebula", "SNR": "supernova_remnant", "Cl+N": "cluster_nebula",
    "HII": "nebula", "RfN": "nebula", "Neb": "nebula",
    "*Ass": "star_cloud", "**": "double_star", "Other": "asterism",
}


def _angle(value: str, hours: bool = False) -> float:
    parts = value.lstrip("+-").split(":")
    first, minutes, seconds = map(float, parts)
    if not all(math.isfinite(n) for n in (first, minutes, seconds)) or not 0 <= minutes < 60 or not 0 <= seconds < 60:
        raise ValueError(f"Invalid sexagesimal angle: {value}")
    sign = -1 if value.startswith("-") else 1
    result = sign * (first + minutes / 60 + seconds / 3600) * (15 if hours else 1)
    if not (0 <= result < 360 if hours else -90 <= result <= 90):
        raise ValueError(f"Angle out of range: {value}")
    return round(result, 6)


def _source_rows(directory: Path, download: bool) -> list:
    rows = []
    for name, expected in SOURCE_HASHES.items():
        path = directory / name
        if not path.exists() and download:
            url = f"https://raw.githubusercontent.com/mattiaverga/OpenNGC/{OPENNGC_REVISION}/database_files/{name}"
            request = urllib.request.Request(url, headers={"User-Agent": "SkyMonitor-catalog-builder"})
            with urllib.request.urlopen(request, timeout=90) as response:
                content = response.read()
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError(f"OpenNGC checksum mismatch: {name}")
            directory.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f"OpenNGC checksum mismatch: {name}")
        rows.extend(csv.DictReader(io.StringIO(content.decode("utf-8")), delimiter=";"))
    return rows


def build_catalog(source_dir: Path, overrides_path: Path, output: Path, download: bool = False) -> list:
    rows = _source_rows(source_dir, download)
    overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
    indexed = {}
    for row in rows:
        if row["M"] and row["Type"] != "Dup":
            number = int(row["M"])
            if number in indexed:
                raise ValueError(f"Duplicate Messier number: M{number}")
            indexed[number] = row
    # OpenNGC treats M102 as a possible duplicate of M101. For a usable M1-M110
    # chart, follow the NASA/Hubble identification with the Spindle Galaxy.
    indexed[102] = next(row for row in rows if row["Name"] == "NGC5866")
    if set(indexed) != set(range(1, 111)):
        raise ValueError("Messier catalogue must contain M1 through M110 exactly once")

    catalog = []
    for number in range(1, 111):
        row = indexed[number]
        object_id = f"M{number}"
        names = overrides["names"].get(object_id, {})
        magnitude = float(row["V-Mag"]) if row["V-Mag"] else None
        if magnitude is None:
            supplement = overrides["visual_magnitudes"].get(object_id)
            magnitude = supplement["value"] if supplement else None
        if magnitude is not None and not math.isfinite(magnitude):
            raise ValueError(f"Invalid magnitude: {object_id}")
        catalog.append({
            "id": object_id,
            "name_en": names.get("name_en") or row["Common names"].split(",")[0].strip() or object_id,
            "name_zh": names.get("name_zh"),
            "object_type": TYPES[row["Type"]],
            "ra_deg": _angle(row["RA"], hours=True),
            "dec_deg": _angle(row["Dec"]),
            "magnitude": magnitude,
            "constellation": "Ser" if row["Const"] in ("Se1", "Se2") else row["Const"],
            "importance": names.get("importance", 2),
        })
    catalog.extend(overrides["extras"])
    if len({row["id"] for row in catalog}) != len(catalog):
        raise ValueError("Duplicate catalogue IDs")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return catalog


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data/raw/openngc")
    parser.add_argument("--output", type=Path, default=ROOT / "data/deep_sky_catalog.json")
    parser.add_argument("--download", action="store_true", help="Download missing pinned source CSVs")
    args = parser.parse_args()
    result = build_catalog(args.source_dir, ROOT / "data/deep_sky_overrides.json", args.output, args.download)
    print(f"Built {len(result)} targets, including all 110 Messier entries: {args.output}")
