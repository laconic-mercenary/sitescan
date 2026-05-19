# sitescan implementation prompt

This file is the working brief for an autonomous implementation pass. It should tell the
agent what the project is, what to build next, how to make engineering decisions, and
how to report incomplete or uncertain work.

## Mission

Build `sitescan`: a binary semantic segmentation pipeline for detecting candidate buried
archaeological structures in satellite imagery.

The product should take prepared multispectral/geospatial raster data as input and
produce georeferenced probability maps as output. The probability maps must align with
the source imagery in GIS tools and support human review of candidate sites.

Primary success is not a perfect model on the first pass. Primary success is a coherent,
testable, reproducible ML pipeline that can ingest data, train, evaluate, run inference,
and preserve geospatial metadata correctly.

## Current Reference Docs

- `README.md`: product goal, model direction, data strategy, inference target.
- `CONCEPTS.md`: remote sensing, segmentation, training, evaluation, and inference
  concepts for this project.
- `configs/model.yaml`: model shape and input channel contract.
- `configs/train.yaml`: training hyperparameters and data-loading contract.

Read these before implementing.

## Tech Stack

- Python 3.10+
- PyTorch
- Lightning
- segmentation-models-pytorch
- timm
- torchmetrics
- rasterio
- numpy
- albumentations
- shapely
- geopandas
- pyyaml
- pytest
- ruff

Package metadata lives in `pyproject.toml`.

## Dev Commands

Run from the repository root.

```bash
pip install -e ".[dev]"
ruff check .
pytest
sitescan-train --config configs/train.yaml --model-config configs/model.yaml
sitescan-predict --checkpoint <checkpoint.ckpt> --input <input.tif> --output <output.tif>
```

If these commands do not exist yet, implement them or adjust this section to match the
actual CLI created during the pass.

## Target Repository Shape

Prefer a small, boring Python package before adding abstractions.

```text
src/
  __init__.py
  cli/
  config/
  data/
  geo/
  models/
  training/
  inference/
  evaluation/
tests/
configs/
```

Suggested responsibilities:

- `config`: typed config loading and validation.
- `data`: tile datasets, mask loading, transforms, train/val/test splitting.
- `geo`: GeoTIFF I/O, CRS/transform preservation, raster/vector helpers.
- `models`: model construction from `configs/model.yaml`.
- `training`: Lightning module, losses, metrics, checkpointing.
- `inference`: sliding-window prediction and output stitching.
- `evaluation`: threshold sweeps, IoU, precision, recall, reports.
- `cli`: command entry points for train, predict, prepare, evaluate.

## Data Contract

The model input is a multi-channel GeoTIFF tile or tile chip. The current intended full
channel contract is 13 channels:

| Channel | Content |
|---------|---------|
| 0 | Dry red, Sentinel-2 B04 |
| 1 | Dry green, Sentinel-2 B03 |
| 2 | Dry blue, Sentinel-2 B02 |
| 3 | Dry NIR, Sentinel-2 B08 |
| 4 | Dry NDRE |
| 5 | Wet red, Sentinel-2 B04 |
| 6 | Wet green, Sentinel-2 B03 |
| 7 | Wet blue, Sentinel-2 B02 |
| 8 | Wet NIR, Sentinel-2 B08 |
| 9 | Wet NDRE |
| 10 | NDRE anomaly, dry NDRE minus wet NDRE |
| 11 | Slope |
| 12 | TPI |

Masks are single-channel binary rasters aligned to imagery:

- `1`: confirmed structure pixel.
- `0`: background.

Hard requirements:

- Preserve CRS, affine transform, dimensions, and nodata semantics when writing outputs.
- Fail loudly if imagery and mask dimensions or transforms do not match.
- Avoid silent resampling unless an explicit command or config requests it.
- Treat geospatial correctness as a product requirement, not as bookkeeping.

## Training Goal

Implement a supervised binary semantic segmentation path:

- Build model from `configs/model.yaml`.
- Use UNet via `segmentation-models-pytorch`.
- Support `in_channels: 13` as the default.
- Use BCEWithLogits plus Dice loss.
- Apply positive class weighting from `configs/train.yaml`.
- Track IoU, precision, recall, and loss for train/val.
- Save best checkpoints by validation IoU.
- Make training reproducible from a fixed seed.

If DINOv2 via `segmentation-models-pytorch` is not immediately compatible with the
13-channel setup, make the smallest practical compatibility layer and document the tradeoff.
Prefer a working path over architectural purity.

## Inference Goal

Implement sliding-window inference over full GeoTIFFs:

- Read a georeferenced multi-channel input raster.
- Chip into overlapping windows.
- Run model inference in batches.
- Blend overlapping predictions deterministically.
- Write a single-channel float probability GeoTIFF in `[0, 1]`.
- Preserve source CRS and transform.

Optional but valuable:

- Output thresholded mask GeoTIFF.
- Support CPU, CUDA, and Apple Silicon MPS where available.
- Emit progress bars and concise runtime summaries.

## Evaluation Goal

Implement evaluation that is useful before the model is good:

- Compute IoU, precision, recall, F1/Dice.
- Support threshold sweeps, not only threshold `0.5`.
- Report confusion counts in pixels.
- Save a machine-readable metrics file, preferably JSON.
- Make it easy to compare checkpoints.

## Data Preparation Goal

If data preparation is in scope for the pass, implement only the next useful slice:

- Chip aligned imagery and masks into fixed-size tiles.
- Respect overlap from `configs/train.yaml`.
- Drop or flag empty/nodata-heavy tiles.
- Split train/val/test reproducibly.
- Write a manifest describing every generated tile.

First concrete data-prep target:

- `rasterize-labels`: convert KML/GeoJSON geoglyph outlines into binary masks.
- `prepare-tiles`: chip aligned imagery and masks into training tiles.
- `gee-export`: produce one reproducible Sentinel-2 export for the first selected site.

Do these in that order if possible. If Google Earth Engine access is not available in the
runtime, implement the command contract and document the manual export steps.

## First Milestone Dataset

Milestone: train and run inference for one validated South American archaeological site,
using historical/satellite imagery plus vector labels. The purpose is an end-to-end real
data vertical slice, not a generalizable production model yet.

First site candidate: Fazenda Colorada, Acre, Brazil.

Why this site:

- It is part of the Acre geoglyph region in southwestern Amazonia.
- The site appears in archaeological literature and published geoglyph databases.
- It has multiple named structures close together: circle, square, double rectangle,
  embankments/roads.
- It is small enough for a first supervised experiment.
- It gives the pipeline a real vector-to-mask problem rather than only synthetic tests.

Known candidate labels from the Amazon Geoglyphs KML:

| KML id | Structure | Approx center |
|--------|-----------|---------------|
| `rbrci` | Rio Branco Circle 160m, Fazenda Colorada | `-9.872980, -67.534413` |
| `rbrsq` | Rio Branco Square 200m, Fazenda Colorada | `-9.875281, -67.534505` |
| `rbrdr` | Rio Branco Double Rectangle 147 x 138m, Fazenda Colorada | `-9.877652, -67.535332` |

Related KML linework near the same site includes closed or nearly closed `LineString`
features named `circle 488m`, `square 796m`, `rectangle 339m`, `rectangle 378m`, and
`embankment 262m`. Treat these as source vector candidates, then inspect visually before
using them as ground truth.

Primary vector source:

- Mendeley Data: "Amazon Geoglyphs", DOI `10.17632/5ynjwk7gc7.1`, CC BY 4.0.
  The dataset description says it includes geoglyph coordinates, sizes, a spreadsheet,
  Google Earth placemarks, outlines for all except the smallest earthworks, and visible
  ancient lines.

Validation / archaeological context sources:

- UNESCO Tentative List: "Geoglyphs of Acre", submitted by Brazil on 2015-01-30.
- Pärssinen, Balée, Ranzi, Barbosa (2020), "The geoglyph sites of Acre, Brazil:
  10 000-year-old land-use practices and climate change in Amazonia", Antiquity.
- Kalliola, Pärssinen, Ranzi, Seppä, Barbosa (2024), "Geography of ancient geometric
  earthworks and their builders in southwestern Amazonia", Acta Amazonica.

Imagery source:

- Google Earth Engine `COPERNICUS/S2_SR_HARMONIZED` for Sentinel-2 Level-2A surface
  reflectance, available from 2017-03-28 onward with a 5-day revisit interval.
- Optional historical comparison: Landsat Collection 2 Surface Reflectance for lower
  resolution longer-term context.

First export contract:

- Area of interest: a small bounding box around the three Fazenda Colorada structures,
  padded enough to include surrounding background.
- Date windows: start with one dry-season composite and one wet-season composite.
- Channels: export the project-standard 13 channels if feasible; otherwise begin with
  spectral-only channels and keep the channel contract explicit in metadata.
- Label output: one binary mask raster aligned to the exported imagery.
- Manifest: write source URLs, dates, AOI bounds, CRS, pixel size, channels, and label
  provenance.

Licensing note:

- Prefer the archived Mendeley dataset for implementation because its page states
  CC BY 4.0. The live `jqjacobs.net` KML is useful for exploration but appears to have
  later updates and should not be treated as the licensed training source until its
  terms are clarified.

## CLI Requirements

Prefer explicit commands with obvious inputs and outputs.

Suggested commands:

```bash
sitescan-train --config configs/train.yaml --model-config configs/model.yaml
sitescan-predict --checkpoint checkpoints/best.ckpt --input data/raw/site.tif --output outputs/site_prob.tif
sitescan-evaluate --checkpoint checkpoints/best.ckpt --data data/tiles --output outputs/eval.json
sitescan-prepare-tiles --image data/raw/site.tif --mask data/masks/site.tif --output data/tiles
```

Every CLI should:

- Validate required paths before doing work.
- Create output directories if appropriate.
- Return non-zero on failure.
- Print concise, useful status messages.

## Engineering Conventions

- Keep implementation straightforward and local to the task.
- Prefer typed dataclasses or small config objects over passing raw nested dictionaries.
- Validate config values at load time.
- Use `pathlib.Path` for filesystem paths.
- Use Python logging for library code; CLI may print high-level progress.
- Avoid global mutable state.
- Raise clear exceptions at boundaries; do not swallow geospatial or data-shape errors.
- Keep functions small enough to test directly.
- Add comments only where the geospatial or ML detail is not obvious.
- Keep imports clean and run `ruff check .`.

## Testing Expectations

Prioritize tests around correctness risks:

- Config loading and validation.
- GeoTIFF read/write metadata preservation.
- Tile window generation and overlap behavior.
- Loss/metric shape handling.
- Dataset image/mask alignment checks.
- CLI argument validation for missing files.

Use small synthetic rasters in tests. Do not require real satellite data for unit tests.

## Performance Expectations

Good enough first:

- Use batching for inference.
- Avoid loading unnecessary duplicate copies of large rasters.
- Keep tile generation deterministic.
- Expose batch size, tile size, overlap, and device as config or CLI options.

Do not prematurely optimize ONNX, Rust inference, TensorRT, or quantization unless the
current task explicitly asks for it.

## Non-Goals For The First Autonomous Pass

- Production deployment.
- Rust inference runtime.
- ONNX export, unless training and PyTorch inference already work.
- Google Earth Engine automation, unless explicitly selected as the first data-prep target.
- A web UI.
- Claims of archaeological validity beyond measured model outputs.

## First Pass Status

Complete. The first pass produced a real Fazenda Colorada vertical slice:

- Earth Engine Sentinel-2/terrain export succeeded.
- Local 13-channel GeoTIFF was downloaded and inspected.
- Fazenda Colorada KML linework was extracted to GeoJSON.
- Binary labels were rasterized against the exported GeoTIFF.
- Image/mask tiles were prepared.
- A small CPU smoke model trained for one epoch.
- Prediction wrote a georeferenced probability GeoTIFF.
- Evaluation wrote a threshold-sweep JSON report.
- `ruff` and `pytest` passed in `.venv312`.

See `docs/FIRST_SMOKE_RUN.md`.

## Next Pass TODOs

Primary milestone: turn the smoke slice into a meaningful first experiment.

1. Validate labels visually.
   - Load the source raster, candidate vectors, and rasterized mask in QGIS.
   - Decide which Fazenda Colorada linework should count as positive class.
   - Remove duplicate or low-confidence features from the label source.
   - Decide whether point labels should be excluded, buffered, or used only for inspection.

2. Expand the dataset around Fazenda Colorada.
   - Rerun the Earth Engine export with a larger buffer so default `512 x 512` tiles fit.
   - Include more negative/background context.
   - Preserve the same 13-channel contract.
   - Record the new export task and local products in `docs/DATA_SOURCES.md`.

3. Improve preprocessing.
   - Replace NaNs from cloud/no-data masks deliberately before tiling, not only at dataset load.
   - Add a tile quality filter for nodata-heavy chips.
   - Add image normalization metadata or a simple per-channel normalization strategy.

4. Create a first experiment config.
   - Keep `configs/model_smoke.yaml` for plumbing checks only.
   - Add an experiment config suitable for CPU-limited training, probably `resnet18` or
     `resnet34` without pretrained weights at first.
   - Defer DINOv2 until the data/label path is visually trusted and a stronger machine is
     available.

5. Run a real small experiment.
   - Train for more than one epoch.
   - Save metrics and threshold sweep.
   - Compare prediction overlay against known Fazenda Colorada structures in QGIS.

Environment:

- Use `.venv312` for all Python/ML work.
- The old `venv` uses Python 3.14 and is not suitable for PyTorch training.
- Local hardware is a 2018 Intel Mac mini CPU, so prefer small model/config experiments.

Must-not-touch areas:

- Anything outside this repo, except local tool installation and downloaded data explicitly
  approved by the user.

Acceptance criteria for the next pass:

- `ruff check .`
- `pytest`
- A larger Fazenda Colorada export exists or a clear blocker is documented.
- Label source has an explicit reviewed/accepted subset.
- Prepared tiles include both positive and negative/context tiles.
- A multi-epoch CPU experiment runs without NaN loss.
- Prediction and evaluation outputs are documented.

## Autonomous Worker Instructions

Act as an opinionated implementation worker.

1. Read the reference docs and existing configs first.
2. Inspect the repository before deciding architecture.
3. Make conservative implementation choices that keep the pipeline runnable.
4. Prefer an end-to-end vertical slice over isolated fragments.
5. When blocked by missing real data, create synthetic fixtures and keep interfaces real.
6. Run formatting, linting, and tests that are practical in the environment.
7. Do not hide uncertainty. Document assumptions and known gaps.
8. Leave the repo in a state where the next pass has obvious commands to run.

## Final Report Format

At the end of the pass, report:

- What was implemented.
- What commands were run and whether they passed.
- Any commands that could not be run and why.
- Files changed.
- Remaining gaps or risky assumptions.
- Recommended next step.
