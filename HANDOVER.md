# Handover — sitescan

This document is for the next Claude instance picking up this project.
Read this before touching any code or config.

---

## What this project is

A binary semantic segmentation model for detecting buried archaeological
structures in tropical rainforest from satellite imagery. The mechanism:
buried stone walls alter soil drainage, stressing the tree roots above them.
Stressed canopy produces less chlorophyll — a subtle spectral shift visible
in Sentinel-2 imagery. Linear/rectangular patterns of that stress correlate
to walls, enclosures, and causeways.

This is a master's thesis project. The user is an experienced cloud/distributed
systems engineer with no ML background. Explain ML concepts as you introduce
them, using engineering analogies. Do not assume ML vocabulary.

---

## Decisions made and why

### Domain and training data: Casarabe culture, Bolivia

Chosen over PACUNAM (Guatemala), Acre geoglyphs (Brazil), and Llanos de Mojos.
Reason: Bolivia's dry season (May–October) gives the longest windows of
cloud-free Sentinel-2 imagery in South America. The 2022 Nature paper
(Prümers et al.) on the Casarabe culture is open access and includes GPS
coordinates of confirmed structures in supplementary materials — this is
the ground truth for training masks.

Caveat: Casarabe is savanna/forest mosaic, not dense rainforest. It is the
right choice for v1 (proves the pipeline works). PACUNAM data is the target
for v2 once the pipeline is validated — that is the actual "rainforest canopy
stress" scenario the thesis describes.

### Temporal compositing strategy

Do not use a single composite. Use two seasonal composites + a difference
channel, stacked as input layers:

- Dry season composite (May–Oct): captures stress at peak
- Wet season composite (Nov–Apr): captures the healthy baseline
- NDVI anomaly (dry NDVI − wet NDVI): persistent stress that does not
  recover in the wet season is the strongest single indicator of structural
  interference. Healthy vegetation recovers; structurally-constrained
  vegetation does not.

The temporal window (3 months, 5 months, full season) is treated as a
hyperparameter to be tuned via ablation study — try multiple configurations
and measure false positive rate. Do not pick one upfront.

All compositing is done in Google Earth Engine before data reaches this
pipeline. Output is exported as GeoTIFF with 11 channels (see below).

### Input channels: 11 total

```
[0]  Red   — dry season composite
[1]  Green — dry season composite
[2]  Blue  — dry season composite
[3]  NIR   — dry season composite  (Sentinel-2 Band B08)
[4]  NDVI  — dry season            (NIR - R) / (NIR + R)
[5]  Red   — wet season composite
[6]  Green — wet season composite
[7]  Blue  — wet season composite
[8]  NIR   — wet season composite
[9]  NDVI  — wet season
[10] NDVI anomaly (dry NDVI − wet NDVI)
```

This was 7 channels before the multi-composite decision. configs/model.yaml
already reflects 11.

### Model: UNet + DINOv2 encoder

Architecture: UNet (two-stage encoder/decoder with skip connections).
Encoder: DINOv2 base (Meta, self-supervised, 142M images). Chosen over
ImageNet ResNet-50 because:
- Training data will be limited (expert-labelled archaeological sites are scarce)
- DINOv2 produces richer features with small fine-tuning datasets
- Cropmark detection is fundamentally texture/colour anomaly discrimination,
  where DINOv2 excels

In smp 0.5.0, DINOv2 is accessed as encoder `tu-dinov2_base` via the timm
bridge. `encoder_weights: null` — DINOv2 loads its own weights internally.

### Tile size: 512×512 pixels

At Sentinel-2's 10m resolution, 512px covers ~5km². This was chosen (over
the original 256) because the detection signal is geometric — the model needs
to see enough spatial context to recognise linearity and regularity, not just
a single stressed pixel.

### Loss function: Dice + BCE combined

Class imbalance is severe — structures occupy ~1–3% of any tile. BCE alone
would let the model achieve high accuracy by predicting all-background. Dice
loss is specifically designed for imbalanced segmentation — it measures
region overlap, not pixel accuracy. Combined 50/50 with BCE.

pos_weight: 8.0 — a missed structure pixel is penalised 8× more than a
missed background pixel. Tune up if the model misses detections; tune down
if false alarms are excessive.

---

## Current file state

### Created and finalised

```
CLAUDE.md              — project brief, background, commands. User fills TODOs.
pyproject.toml         — all dependencies with verified latest versions
configs/model.yaml     — fully commented for a beginner, reflects all decisions
configs/train.yaml     — fully commented for a beginner, reflects all decisions
```

### Not yet created (next task)

```
src/__init__.py
src/dataset.py         — IN PROGRESS at time of handover (see below)
src/model.py
src/train.py
src/predict.py
src/utils/__init__.py
src/utils/tiling.py
src/utils/transforms.py
src/utils/viz.py
data/raw/.gitkeep
data/tiles/.gitkeep
data/annotations/.gitkeep
notebooks/
```

---

## Next task: src/dataset.py

This is where work stopped. The user approved starting this file.

The dataset class must:
1. Accept a list of tile paths and an annotation directory
2. Read GeoTIFF tiles with rasterio — tiles have 11 channels in the order
   defined above
3. Read corresponding binary mask (same filename, annotation_dir/)
4. Apply per-tile percentile normalisation (2nd–98th percentile stretch)
   rather than global min/max — aerial imagery brightness varies enormously
   between sites and seasons; percentile stretch preserves relative tone
   differences that define the stress signal
5. Apply albumentations transforms (train augmentation or no-op for val/test)
6. Return dict: {"image": tensor (11, H, W), "mask": tensor (1, H, W), "filename": str}

The build_dataloaders() function must:
- Shuffle and split tile list into train/val/test (seeded, reproducible)
- Attach augmentations to train split only
- Return three DataLoaders

Note: albumentations 2.0.8 (latest) has breaking API changes from 1.x:
- CoarseDropout: max_holes → num_holes_range=(min, max)
- CoarseDropout: max_height → hole_height_range=(min, max)
- GaussNoise: var_limit → std_range=(min, max)

### After dataset.py, order of remaining files

1. src/utils/transforms.py  — albumentations augmentation pipelines
2. src/utils/tiling.py      — chip Sentinel-2 GeoTIFFs into 512×512 tiles
3. src/model.py             — thin smp wrapper, loads from model.yaml
4. src/train.py             — Lightning module + trainer, loads from both configs
5. src/predict.py           — sliding-window inference, outputs probability GeoTIFF
6. src/utils/viz.py         — overlay predictions on RGB imagery
7. Placeholder files        — __init__.py files, .gitkeep files

---

## User preferences (save to memory if your system supports it)

- Experienced cloud/distributed systems engineer, ML novice
- Wants ML concepts explained as they appear, using engineering analogies
- Comments in config files should be written for a beginner
- Inline code comments should explain WHY, not WHAT
- Does not want excessive questions before starting — use reasonable defaults
  and explain the choices made
- Session was using Claude Sonnet 4.6 in VSCode extension

---

## Package versions (verified against pip index on 2026-05-07)

```
torch                      2.11.0
torchgeo                   0.6.2
segmentation-models-pytorch 0.5.0
lightning                  2.6.1
torchmetrics               1.9.0
rasterio                   1.4.4
albumentations             2.0.8
```
