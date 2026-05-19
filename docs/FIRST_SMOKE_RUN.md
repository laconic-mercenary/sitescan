# First Smoke Run

This records the first local end-to-end run for Fazenda Colorada.

## Environment

- Python: `.venv312`
- Interpreter: Homebrew Python 3.12
- Platform: Intel Mac mini CPU
- Training config: `configs/train.yaml`
- Smoke model config: `configs/model_smoke.yaml`

The smoke model uses an untrained `resnet18` encoder and exists only to verify the
pipeline locally. It is not an archaeological model.

## Data Products

```text
data/raw/fazenda_colorada/fazenda_colorada_s2_13ch.tif
data/interim/fazenda_colorada/fazenda_colorada_vectors.geojson
data/interim/fazenda_colorada/fazenda_colorada_mask.tif
data/tiles/fazenda_colorada/manifest.json
```

Source raster:

- CRS: `EPSG:32719`
- Size: `451 x 492`
- Bands: `13`
- Pixel size: `10m`
- NaN pixels in raw export: `242604`

Mask:

- Positive pixels: `1134`

Tiles:

- Tile size: `256`
- Overlap: `64`
- Tile count: `9`
- Positive tiles: `9`

## Commands

```bash
.venv312/bin/python -m src.cli.extract_fazenda_labels
```

```bash
.venv312/bin/python -m src.cli.rasterize_labels \
  --vectors data/interim/fazenda_colorada/fazenda_colorada_vectors.geojson \
  --reference data/raw/fazenda_colorada/fazenda_colorada_s2_13ch.tif \
  --output data/interim/fazenda_colorada/fazenda_colorada_mask.tif
```

```bash
.venv312/bin/python -m src.cli.prepare_tiles \
  --image data/raw/fazenda_colorada/fazenda_colorada_s2_13ch.tif \
  --mask data/interim/fazenda_colorada/fazenda_colorada_mask.tif \
  --output data/tiles/fazenda_colorada \
  --tile-size 256 \
  --overlap 64
```

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

Successful smoke result:

```text
train/loss: 0.877
val/loss: 0.871
val/iou: 0.008
```

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

```bash
.venv312/bin/python -m src.cli.evaluate_mask \
  --prediction outputs/fazenda_colorada_smoke_prob.tif \
  --mask data/interim/fazenda_colorada/fazenda_colorada_mask.tif \
  --output outputs/fazenda_colorada_smoke_eval.json
```

Best threshold from the smoke run:

```text
threshold: 0.4
IoU: 0.005375324699948806
precision: 0.005375324699948806
recall: 1.0
```

These metrics are intentionally poor because the model is tiny, randomly initialized,
and trained for one epoch on one site. The result verifies plumbing, not model quality.

## Verification

```bash
.venv312/bin/python -m ruff check .
.venv312/bin/python -m pytest -q
```

Result:

```text
ruff: all checks passed
pytest: 7 passed
```

