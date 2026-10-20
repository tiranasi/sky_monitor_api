# Deep-sky catalogue sources

`deep_sky_catalog.json` contains M1–M110 plus the four non-Messier targets from
the original application. It is a checked-in, offline catalogue, not a network
query made while serving a sky chart.

## OpenNGC

- Author: Mattia Verga and OpenNGC contributors.
- Source: https://github.com/mattiaverga/OpenNGC
- Pinned revision: `be3cd6c5498806a2fbb2f7e0452ef802dbb02be0`.
- Files: `database_files/NGC.csv` and `database_files/addendum.csv`.
- Licence: CC BY-SA 4.0; copy in `licenses/OpenNGC-CC-BY-SA-4.0.txt`.
- The derived Messier catalogue is distributed under CC BY-SA 4.0. This does
  not change the licence of the application's Python source code.

Positions use the source's J2000 coordinates. Magnitudes use the V band only;
B/J/H/K values are not silently substituted. Decimal coordinates are rounded
to six places. Types are translated to application types; M40 remains a double
star and M73 an asterism. Existing Chinese/common names and four extra targets
are preserved in `deep_sky_overrides.json`.

## Explicit supplements

OpenNGC omits V magnitudes for M22, M35, M62, M69, M70, M71 and M107. Their
apparent magnitudes are supplemented from NASA's Hubble Messier catalogue;
the value and per-object URL are recorded in `deep_sky_overrides.json`.
Unknown magnitudes remain null rather than being inferred from another band.

M102's historical identification is disputed. OpenNGC's addendum identifies it
as a possible duplicate of M101. This application instead follows the
NASA/Hubble Spindle Galaxy identification with NGC 5866, using NGC 5866's
OpenNGC coordinates and V magnitude. It is one entry under M102, not a second M101.

- https://science.nasa.gov/mission/hubble/science/explore-the-night-sky/hubble-messier-catalog/messier-102/
- https://science.nasa.gov/missions/hubble/hubble-sees-galaxy-on-edge/

## Rebuild

```bash
python scripts/build_deep_sky_catalog.py --download
```

Only missing source CSVs are downloaded, from the pinned revision. SHA-256
checksums are verified before processing. Rebuilding without `--download`
uses local files in ignored `data/raw/openngc/`.
