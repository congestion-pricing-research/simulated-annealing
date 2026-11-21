# Cordon optimization with simulated annealing

Optimize a connected, hole-free congestion-pricing cordon using tile-level origin–destination (OD) trips. The search alternates between maximizing captured trips and penalizing the cordon perimeter.

## Quick start

Requires Python 3.11 or later and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run cordon-annealing demo --phases 2 --steps-unpenalized 10 --steps-penalized 10
```

Results are saved to `output/demo/`. To run the bundled synthetic OD example:

```bash
uv run cordon-annealing demo --size 4 --od-csv data/example_od.csv --phases 2 --steps-unpenalized 10 --steps-penalized 10
```

## San Francisco data

The San Francisco experiment requires two external files. The default locations are under `input/sf/`, which Git ignores.

| Input | Default path | Source |
|---|---|---|
| Transportation analysis zone (TAZ) polygons | `input/sf/transportation_analysis_zones_1454.shp` | [Metropolitan Transportation Commission (MTC) 1,454-zone layer](https://www.arcgis.com/home/item.html?id=94e6e7107f0745b5b2aabd651340b739) |
| Individual trip table | `input/sf/indivTripData_3.csv` | MTC travel-model export; not included. See the [MTC data repository](https://data.mtc.ca.gov/data-repository/). |

Use the full TAZ layer, including zones outside San Francisco used to assign entry locations. For shapefiles, keep the `.shp`, `.shx`, `.dbf`, and `.prj` files together (`.cpg` if available).

Required columns:
- Zones: `county`, `taz1454`.
- Trips: `orig_taz`, `dest_taz`, `trip_mode`, `depart_hour`.

The exact public download for `indivTripData_3.csv` has not been identified. Use the corresponding individual-trip export from the 1,454-zone model.

Alternatively, save the [zone layer as GeoJSON](https://services3.arcgis.com/i2dkYWmb4wHvYPda/ArcGIS/rest/services/transportation_analysis_zones_1454/FeatureServer/0/query?where=1%3D1&outFields=county%2Ctaz1454&returnGeometry=true&f=geojson) at `input/sf/transportation_analysis_zones_1454.geojson` and set `--taz-file` to that path.

## Run San Francisco

With inputs at their default paths:

```bash
uv run --extra sf cordon-annealing sf
```

With inputs elsewhere:

```bash
uv run --extra sf cordon-annealing sf \
  --taz-file /path/to/transportation_analysis_zones_1454.shp \
  --trip-file /path/to/indivTripData_3.csv
```

**Grid and start:** The 200 × 200 candidate grid is reduced to its largest edge-connected component (expected: 804 tiles). The bundled start encloses 402 tiles with 46 counted boundary edges. To change it, use `--initial-ea path.csv`, `--square-count`, or `--square-center`.

**Trips:** The loader selects trips destined for San Francisco with `trip_mode < 7` and `depart_hour < 12`, and maps outside origins to four entry zones. It places endpoints within their zones, assigns them to the nearest full-grid centroids, samples half the trips without replacement, and excludes sampled trips with endpoints outside the retained city tiles.

**Optimization:** The default run has 40 oscillations. Each uses 100 unpenalized iterations and 300 perimeter-penalized iterations (80 phases in total). `--phases 2` runs one oscillation. See `uv run --extra sf cordon-annealing sf --help` for additional options.

**Random seed:** A new seed is generated for each run unless `--seed` is provided. The seed is printed at startup and stored in `summary.json`; use it with the same inputs and options to repeat a run.

## Outputs

Results are saved to `output/sf/` by default:

- `summary.json`: configuration and initial/final metrics.
- `initial_cordon.csv` and `optimized_cordon.csv`: cordon masks.
- `phase_history.csv` and optionally `step_history.csv`: optimization history.
- `cordons.png` and `phase_history.png`: plots.

Use `--output` to change the destination or `--no-step-history` to disable step history.

See [Optimization method](docs/method.md) and [Input formats](data/README.md) for details.

## Tests

```bash
uv sync --extra sf --extra dev
uv run --no-sync pytest -q
```