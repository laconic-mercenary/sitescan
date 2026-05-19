# sitescan

`sitescan` is a binary semantic segmentation pipeline for detecting candidate buried
archaeological structures in satellite imagery.

The project is currently in its first real-data stage. The initial vertical slice uses
**Fazenda Colorada**, a known geoglyph site in Acre, Brazil, to prove that the pipeline
can move from public geospatial sources to georeferenced model output:

1. Export a 13-channel Sentinel-2/terrain GeoTIFF from Google Earth Engine.
2. Extract candidate geoglyph vectors from KML.
3. Rasterize those vectors into an aligned binary mask.
4. Chip imagery and masks into tiles.
5. Train a small CPU smoke model.
6. Run sliding-window prediction.
7. Evaluate a threshold sweep against the mask.

The smoke model is not archaeologically useful yet. It exists to verify the plumbing.

---

## Current Status

Working:

- Earth Engine export script for Fazenda Colorada.
- KML-to-GeoJSON candidate label extraction.
- GeoJSON-to-mask rasterization aligned to a reference GeoTIFF.
- Image/mask tile preparation.
- PyTorch Lightning training loop.
- Sliding-window GeoTIFF prediction.
- Threshold-sweep mask evaluation.
- Tests and linting.

Verified locally:

```text
ruff: all checks passed
pytest: 7 passed
```

The first smoke run is documented in:

```text
docs/FIRST_SMOKE_RUN.md
```

---

## Environment

Use Python 3.12 for ML work. PyTorch wheels were not available for the local Python 3.14
environment used during setup.

Recommended local venv:

```bash
/usr/local/bin/python3.12 -m venv .venv312
.venv312/bin/python -m pip install --upgrade pip setuptools wheel
.venv312/bin/python -m pip install -e ".[dev]"
```

Run commands through `.venv312/bin/python`.

The repository pins the local-compatible stack:

- Python `>=3.10,<3.14`
- PyTorch `>=2.2,<2.3`
- torchvision `>=0.17,<0.18`
- NumPy `>=1.26,<2`
- rasterio `>=1.4,<1.5`

---

## Data

Generated rasters, tiles, checkpoints, logs, and outputs are intentionally not committed.

Expected local products after following the data-source runbook:

```text
data/raw/fazenda_colorada/fazenda_colorada_s2_13ch.tif
data/interim/fazenda_colorada/fazenda_colorada_vectors.geojson
data/interim/fazenda_colorada/fazenda_colorada_mask.tif
data/tiles/fazenda_colorada/manifest.json
```

See:

```text
docs/DATA_SOURCES.md
```

---

## Channel Contract

The current model input is a 13-channel GeoTIFF:

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

Output is a single-channel probability GeoTIFF aligned to the source raster.

---

## Commands

Extract Fazenda Colorada candidate vectors:

```bash
.venv312/bin/python -m src.cli.extract_fazenda_labels
```

Export imagery from Earth Engine:

```bash
.venv312/bin/python scripts/export_fazenda_colorada_s2.py
```

Rasterize labels:

```bash
.venv312/bin/python -m src.cli.rasterize_labels \
  --vectors data/interim/fazenda_colorada/fazenda_colorada_vectors.geojson \
  --reference data/raw/fazenda_colorada/fazenda_colorada_s2_13ch.tif \
  --output data/interim/fazenda_colorada/fazenda_colorada_mask.tif
```

Prepare tiles:

```bash
.venv312/bin/python -m src.cli.prepare_tiles \
  --image data/raw/fazenda_colorada/fazenda_colorada_s2_13ch.tif \
  --mask data/interim/fazenda_colorada/fazenda_colorada_mask.tif \
  --output data/tiles/fazenda_colorada \
  --tile-size 256 \
  --overlap 64
```

Run the CPU smoke train:

```bash
.venv312/bin/python -m src.train \
  --config configs/train.yaml \
  --model-config configs/model_smoke.yaml \
  --tile-dir data/tiles/fazenda_colorada \
  --max-epochs 1 \
  --batch-size 1 \
  --num-workers 0 \
  --accelerator cpu
```

Run smoke prediction:

```bash
.venv312/bin/python -m src.predict \
  --checkpoint checkpoints/epoch=0-step=8-v1.ckpt \
  --config configs/train.yaml \
  --model-config configs/model_smoke.yaml \
  --input data/raw/fazenda_colorada/fazenda_colorada_s2_13ch.tif \
  --output outputs/fazenda_colorada_smoke_prob.tif \
  --tile-size 256 \
  --overlap 64 \
  --device cpu
```

Evaluate prediction against the mask:

```bash
.venv312/bin/python -m src.cli.evaluate_mask \
  --prediction outputs/fazenda_colorada_smoke_prob.tif \
  --mask data/interim/fazenda_colorada/fazenda_colorada_mask.tif \
  --output outputs/fazenda_colorada_smoke_eval.json
```

Verify:

```bash
.venv312/bin/python -m ruff check .
.venv312/bin/python -m pytest -q
```

---

## Repository Structure

```text
configs/        model and training configs
docs/           data-source notes and run records
scripts/        one-off/reproducible data export scripts
src/
  cli/          command entry points
  config/       typed config loading
  data/         tiling and tile manifests
  evaluation/   metrics and threshold sweeps
  geo/          KML parsing and rasterization
  models/       segmentation model factory
  training/     datasets, losses, Lightning module
tests/          lightweight tests
```

---

## Next Milestone

The next pass should turn the smoke slice into a meaningful first experiment:

- Inspect the Fazenda Colorada vectors and mask in QGIS.
- Create a reviewed/accepted label subset.
- Rerun Earth Engine export with a larger AOI for more background context.
- Prepare tiles with both positive and negative/context examples.
- Add a small CPU experiment config distinct from `model_smoke.yaml`.
- Run a multi-epoch experiment with finite loss and documented metrics.

See:

```text
PROMPT.md
CONCEPTS.md
```

---

## References

- Google Earth Engine: https://earthengine.google.com/
- Sentinel-2 mission: https://sentinel.esa.int/web/sentinel/missions/sentinel-2
- Mendeley Amazon Geoglyphs dataset: https://data.mendeley.com/datasets/5ynjwk7gc7/1
- QGIS: https://qgis.org/
- PyTorch: https://pytorch.org/
- segmentation-models-pytorch: https://github.com/qubvel-org/segmentation_models.pytorch
- rasterio: https://rasterio.readthedocs.io/

---

## License

[MIT](LICENSE)
