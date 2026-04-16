# DeadTrees Prepackaged: Agent Seed

## Goal
- Standalone Python package to build prepackaged deadtrees datasets.
- Backend is expected to call package/CLI directly.
- No HTTP/API endpoint in this repo.
- Current implemented datasets:
  - `tree-cover-aerial-global`
  - `standing-deadwood-aerial-global-conservative`

## Current State
- Access method: direct PostgreSQL, not Supabase REST.
- Output contract: build writes exactly one final ZIP to the root of `--output-root`.
- GeoPackage layers are written incrementally per dataset using append mode; polygon GeoDataFrames are not accumulated across all datasets before export.
- Current live-tested path works against existing `DEADTREES_DB_*` env vars when `DEADTREES_DB_SSLMODE=disable`.
- Test mode works and limits to first 10 eligible dataset IDs.
- For `standing-deadwood-aerial-global-conservative`, eligible datasets remain in AOI/metadata output even if they contribute zero deadwood polygons after clipping/cleanup.

## Important Files
- Package entry:
  - [deadtrees_prepackaged/__init__.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/__init__.py)
  - [deadtrees_prepackaged/runner.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/runner.py)
  - [deadtrees_prepackaged/cli.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/cli.py)
- Dataset implementation:
  - [deadtrees_prepackaged/datasets/tree_cover_aerial_global.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/datasets/tree_cover_aerial_global.py)
  - [deadtrees_prepackaged/datasets/standing_deadwood_aerial_global_conservative.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/datasets/standing_deadwood_aerial_global_conservative.py)
- DB access:
  - [deadtrees_prepackaged/postgres/client.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/postgres/client.py)
  - [deadtrees_prepackaged/postgres/queries.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/postgres/queries.py)
- Export helpers:
  - [deadtrees_prepackaged/helpers/geometry.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/helpers/geometry.py)
  - [deadtrees_prepackaged/helpers/labels.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/helpers/labels.py)
  - [deadtrees_prepackaged/helpers/metadata.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/helpers/metadata.py)
  - [deadtrees_prepackaged/helpers/geopackage.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/helpers/geopackage.py)
  - [deadtrees_prepackaged/helpers/manifest.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/helpers/manifest.py)
  - [deadtrees_prepackaged/helpers/orthophotos.py](/net/home/cmosig/projects/prepackaged_datasets_dte/deadtrees_prepackaged/helpers/orthophotos.py)
- Packaging/tests:
  - [pyproject.toml](/net/home/cmosig/projects/prepackaged_datasets_dte/pyproject.toml)
  - [tests/test_postgres_client.py](/net/home/cmosig/projects/prepackaged_datasets_dte/tests/test_postgres_client.py)
  - [tests/test_tree_cover_build.py](/net/home/cmosig/projects/prepackaged_datasets_dte/tests/test_tree_cover_build.py)
  - [tests/test_metadata.py](/net/home/cmosig/projects/prepackaged_datasets_dte/tests/test_metadata.py)

## Runtime / Env
- DB env vars match `/net/home/cmosig/projects/sentinel_mortality/scripts/syncdeadtrees/2_sync_audited_geopackages.sh`:
  - `DEADTREES_DB_HOST`
  - `DEADTREES_DB_PORT`
  - `DEADTREES_DB_NAME`
  - `DEADTREES_DB_USER`
  - `DEADTREES_DB_PASSWORD`
  - optional: `DEADTREES_DB_SSLMODE`
- Current tested DB endpoint required:
  - `DEADTREES_DB_SSLMODE=disable`
- Python env used successfully for live runs:
  - `/net/home/cmosig/miniconda3/envs/scienceagent/bin/python`

## Install / Test / Run
- Install package:
```bash
pip install -e .
```
- Install with test deps:
```bash
pip install -e .[test]
```
- Run tests:
```bash
/net/home/cmosig/miniconda3/envs/scienceagent/bin/python -m pytest -q
```
- Test build:
```bash
DEADTREES_DB_SSLMODE=disable \
/net/home/cmosig/miniconda3/envs/scienceagent/bin/python -m deadtrees_prepackaged.cli build tree-cover-aerial-global \
  --storage-root /tmp \
  --output-root /tmp/deadtrees_prepackaged_out \
  --working-dir /tmp/deadtrees_prepackaged_work \
  --test-mode
```
- Test build for standing deadwood:
```bash
DEADTREES_DB_SSLMODE=disable \
/net/home/cmosig/miniconda3/envs/scienceagent/bin/python -m deadtrees_prepackaged.cli build standing-deadwood-aerial-global-conservative \
  --storage-root /tmp \
  --output-root /tmp/deadtrees_prepackaged_out \
  --working-dir /tmp/deadtrees_prepackaged_work \
  --test-mode
```

## Current Dataset Logic
- `tree-cover-aerial-global`
  - Eligibility query lives in `deadtrees_prepackaged/datasets/tree_cover_aerial_global.py`
  - Eligibility source: `v_export_polygon_candidates`
  - Explicit filters:
    - `layer_type = 'forest_cover'`
    - `forest_cover_quality in ('great', 'sentinel_ok')`
    - `v2_datasets.license = 'CC BY'`
    - `v2_datasets.data_access = 'public'`
  - No explicit platform filter.
- `standing-deadwood-aerial-global-conservative`
  - Eligibility query lives in `deadtrees_prepackaged/datasets/standing_deadwood_aerial_global_conservative.py`
  - Eligibility source: `v_export_polygon_candidates`
  - Explicit filters:
    - `layer_type = 'deadwood'`
    - `deadwood_quality in ('great', 'sentinel_ok')`
    - `v2_datasets.license = 'CC BY'`
    - `v2_datasets.data_access = 'public'`
    - acquisition year/month/day all present
    - phenology indicator at acquisition day-of-year is `> 128`, applied locally in Python after candidate rows are fetched
  - Eligible datasets are retained in AOI and metadata outputs even when no deadwood polygons remain after AOI clipping/geometry cleanup.
- Shared behavior:
  - AOI fetched from `v2_aois`, assumed single relevant AOI.
  - Exported polygons are clipped to the AOI after loading.
  - Metadata joined from `v2_datasets`, `v2_orthos`, `v2_metadata`, `data_publication`.
  - `deadtrees_prepackaged/postgres/queries.py` only contains shared query execution helpers, not export-specific SQL filters.
  - Shared baseline dataset SQL filters live in `deadtrees_prepackaged/postgres/filters.py` and currently enforce `license = 'CC BY'`, `data_access = 'public'`, `archived = false`, and acquisition date presence.
  - Shared dataset SQL filters in `deadtrees_prepackaged/postgres/filters.py` are intended to be applied against `v2_full_dataset_view` and additionally enforce `is_audited = true` by default so exports can use dataset-level audit state without depending on polygon-candidate audit fields.

## Current Export Schema
- Final deliverable: one ZIP in output root.
- ZIP contents:
  - `<package_name>.gpkg`
  - `LICENSE.txt`
  - `METADATA.csv`
  - `METADATA.parquet`
  - `manifest.json`
  - `LICENSE.txt` is always included for all packages and contains package attribution text, all unique authors in alphabetical order as a comma-separated list, all existing DOI values plus `deadtrees.earth` as sources, package-specific reference citations, and the full `CC BY 4.0` license text.
  - `manifest.json` includes a `source_reference` object with the dataset-definition file path and installed package version.
- Current `tree_cover` layer columns:
  - `dataset_id`
  - `geometry`
- Current `standing_deadwood` layer columns:
  - `dataset_id`
  - `geometry`
- Current `aoi` layer columns:
  - `dataset_id`
  - `geometry`
- Current metadata columns:
  - `dataset_id`
  - `authors`
  - `acquisition_year`
  - `acquisition_month`
  - `acquisition_day`
  - `additional_information`
  - `citation_doi`
  - `freidata_doi`
  - `bbox`
  - `biome_name`
  - `forest_cover_quality`
  - `license`
  - `platform`

## Cleanup / Safety
- Successful build cleanup:
  - working dir is deleted
  - only ZIP remains in output root
- DB safety:
  - Postgres connection is explicitly `read_only = True`
  - test exists for this
- PgBouncer compatibility:
  - `prepare_threshold=None` is required in psycopg connection

## Tests Present
- `test_connect_postgres_sets_read_only`
- `test_metadata_row_omits_file_name`
- `test_build_creates_single_zip_and_cleans_intermediate_files`
- `test_build_geopackage_layers_have_expected_columns`
- `test_list_datasets_includes_deadwood_export`
- `test_deadwood_build_creates_expected_layer`

## Known Conversation Decisions
- No backend HTTP endpoint in this repo.
- Keep implementation minimal.
- Do not export `file_name` in metadata.
- Do not export `id`, `label_id`, `area_m2`, `properties` for tree-cover polygons.
- Do not export `image_quality`, `notes` for AOI.
- `fid` may still exist in GeoPackage internals; that is file-format internal, not source schema.
- Output ZIP should be at root of output directory, not nested.
- PostgreSQL was chosen over Supabase REST because:
  - unrestricted direct DB access
  - avoids public-view mismatch
  - avoids PostgREST timeout/visibility quirks

## Working Rules For Next Agents
- Use git for every logical change; keep commits small and descriptive.
- Keep this `AGENTS.md` up to date whenever architecture, env vars, output schema, or run instructions change.
- If changing exported schema, update tests first or alongside code.
- Prefer direct PostgreSQL reads; do not reintroduce Supabase REST unless explicitly requested.
- Preserve minimalism: avoid adding fields/endpoints/registry tables unless asked.
- Before claiming runtime success, run either:
  - `pytest`, and/or
  - the real `--test-mode` build against the live DB env.
