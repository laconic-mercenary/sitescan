# sitescan

## My background 

Many years of software engineering, building cloud based systems processing high throughput and keeping high availability - but ML I don't understand, outside of the following concepts

- That models are usually trained
- That the idea is to build something that predicts or classifies an outcome, based on statistical models and training / test data.
- That model inference refers to invoking the model 
- Training data is broken into 2 sets - training and test data. 
- Other general concepts. 

Please teach me has we go. 

## Project background

Aerial imagery analysis for archaeological prospection. The model identifies potential fieldwork sites from aerial/satellite imagery by detecting cropmarks, soilmarks, and parchmarks — surface discoloration patterns caused by buried features (ditches, pits, walls, foundations).

<!-- TODO: add details about the specific study region, imagery sources, target feature types, and any known site datasets being used for training -->

## Data

- **Domain**: Tropical rainforest — detecting buried walls/structures via canopy stress signatures
- **Signal**: Buried stone structures alter soil drainage and depth, stressing tree roots above them. Stressed canopy produces less chlorophyll → subtle RGB shift toward lighter/yellow-green. The geometry of the stress mirrors the structure (linear walls → linear stress bands).
- **Input**: Sentinel-2 GeoTIFF tiles — 4 raw bands (R, G, B, NIR) + 3 computed vegetation indices (NDVI, VARI, ExG) = 7 channels total
- **Labels**: Binary masks derived from LiDAR surveys of known sites — pixel is 1 if it overlaps a confirmed structure footprint
- **Source imagery**: Sentinel-2 (10m resolution, free, global coverage — Bands B04/B03/B02/B08)
- **Ground truth source**: LiDAR surveys (OpenTopography, PACUNAM LiDAR Initiative, Amazon geoglyphs dataset)

## Task

Binary semantic segmentation: classify each pixel as "structural stress pattern" or background. The detection signal is both spectral (chlorophyll-depleted canopy) and geometric (linearity/regularity distinguishes structural stress from random environmental variation). Class imbalance is severe — structures occupy a tiny fraction of any tile.

## Libraries

| Library | Version | Role |
|---|---|---|
| `torch` | ≥2.11 | Core deep learning framework |
| `torchgeo` | ≥0.6.2 | Geospatial dataset utilities, samplers |
| `segmentation-models-pytorch` | ≥0.5.0 | UNet / FPN / DeepLabV3+ model factory |
| `lightning` | ≥2.6 | Training loop, checkpointing, logging |
| `torchmetrics` | ≥1.9 | IoU, F1 metrics |
| `rasterio` | ≥1.4 | GeoTIFF read/write, preserving georeferencing |
| `albumentations` | ≥2.0 | Spatial + colour augmentations |
| `geopandas` / `shapely` | ≥0.14 / ≥2.0 | Vector annotation handling |
| `numpy` | ≥1.26 | Array ops |
| `matplotlib` | ≥3.8 | Visualisation |

## Model

Default: UNet with ResNet-50 encoder (ImageNet pretrained), binary output with Dice + BCE loss.
Config lives in `configs/model.yaml` — swap architecture/encoder there without touching code.

<!-- TODO: note any specific architecture decisions, pretrained weights, or constraints -->

## Project structure

```
configs/           # training hyperparams (train.yaml) and model config (model.yaml)
data/
  raw/             # original GeoTIFFs — not committed to git
  tiles/           # chipped 256×256 training patches
  annotations/     # binary masks (same filename as tile)
src/
  dataset.py       # PyTorch Dataset + dataloader builder
  model.py         # model factory (smp wrappers)
  train.py         # Lightning training loop
  predict.py       # sliding-window inference on full GeoTIFFs
  utils/
    tiling.py      # chip large GeoTIFFs into overlapping patches
    transforms.py  # albumentations augmentation pipelines
    viz.py         # overlay predictions on imagery
notebooks/         # EDA and result inspection
```

## Commands

```bash
# install
pip install -e ".[dev]"

# chip raw imagery into tiles
python -m src.utils.tiling data/raw/site_001.tif

# train
python -m src.train --train-cfg configs/train.yaml --model-cfg configs/model.yaml

# predict on a new image
python -m src.predict path/to/image.tif checkpoints/best.ckpt
```

## Notes

<!-- TODO: any quirks, known issues, coordinate systems used, nodata handling, etc. -->
