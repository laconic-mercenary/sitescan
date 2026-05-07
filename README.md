# sitescan

A binary semantic segmentation pipeline for detecting buried archaeological structures
in satellite imagery — using freely available satellite data, with a path toward
incorporating LiDAR where survey coverage exists.

---

## Background

Thousands of pre-Columbian sites remain undiscovered across South America, hidden beneath
forest canopy and centuries of vegetation. Traditional survey methods — ground survey,
aerial photography, LiDAR — are expensive, slow, and limited in geographic reach.
Satellite imagery is global and free. The question is whether a model can learn to read it.

The signal exists. Buried stone structures alter soil drainage and depth, stressing the
roots of trees growing above them. That stress reduces chlorophyll production, producing
a subtle spectral shift in the canopy — a slightly lighter, more yellow-green tone in
the red and near-infrared bands. When that stress pattern is linear or rectangular, it
mirrors the geometry of the structure beneath: a wall becomes a stress band, an enclosure
becomes a stress rectangle.

This is not a new observation. Archaeologists call these cropmarks and soilmarks; they
have been identified in European aerial photography since the 1920s. What is new is
applying learned image segmentation to detect them at scale in satellite data over
tropical forest.

---

## Goal

Train a model that (initially) takes a multi-spectral satellite image tile as input and produces a
probability map as output: each pixel receives a score between 0 (background) and 1
(probable buried structure). A threshold applied to that map produces a binary detection
mask that can be overlaid on a map and reviewed.

This is a **binary semantic segmentation** task. The model does not identify individual
structures or classify structure types — it flags pixels where the spectral and geometric
signature of structural stress is present.

### Input

A satellite image of a region of interest — exported from Google Earth Engine as a
GeoTIFF file. The user selects the area and date range; everything else is automated.

### Output

A georeferenced probability map in GeoTIFF format, the same size and position as the
input image. Each pixel contains a value between 0 and 1. Loaded into any GIS tool
(QGIS, ArcGIS, Google Earth), it overlays directly on the source imagery — bright areas
are candidate sites for field review.

---

## Approach

The detection signal has two components that the model must learn simultaneously:

**Spectral**: stressed canopy has reduced NIR reflectance and lower NDVI (Normalized
Difference Vegetation Index) relative to healthy surrounding forest.

**Geometric**: random environmental stress (drought patches, disease, terrain variation)
also depresses NDVI. What distinguishes structural stress is its geometry — linear,
rectangular, or regular patterns that match the shapes of walls and enclosures. A single
stressed pixel is noise. A stressed line is a wall.

The model architecture is chosen to capture both signals. A UNet works in two stages:
the encoder reads the image at progressively coarser scales, building up an understanding
of what is where; the decoder works back to full resolution, using that understanding to
label every pixel. Direct connections between matching encoder and decoder stages
(skip connections) ensure that fine spatial detail — the exact edges of a stress line —
is not lost during the compression stage.

Class imbalance is a problem here: structures occupy roughly 1–3% of any tile, so a
model that predicts "background" for every pixel would be 97% accurate while being
completely useless. The loss function (the error signal the model minimises during
training) combines Dice loss — which measures region overlap and is specifically designed
for imbalanced data — with Binary Cross-Entropy, weighted to penalise missed structures
more heavily than false alarms.

---

## Model

**Architecture**: UNet  
**Encoder**: DINOv2 base (`tu-dinov2_base` via [timm](https://github.com/huggingface/pytorch-image-models), 142M-image self-supervised pretraining)  
**Input**: 11-channel GeoTIFF tiles at 512×512 pixels  
**Output**: single-channel probability map, same spatial resolution as input

Used via [segmentation-models-pytorch](https://github.com/qubvel-org/segmentation_models.pytorch) (smp), which provides the UNet + encoder wiring and handles the adapter from 11 input channels to DINOv2's expected input.

### Why DINOv2

Training data will be scarce. Expert-labelled archaeological sites are rare — each
confirmed site covers a small geographic area and requires independent survey to validate.
DINOv2 ([Oquab et al., 2023](https://arxiv.org/abs/2304.07193)) was trained
self-supervised (without human labels — it learned by comparing patches of images to each
other) on 142 million images. That produces rich texture and colour-gradient
representations that transfer well to new tasks with limited labelled data.

The cropmark detection problem — spotting subtle colour anomalies arranged in geometric
patterns — is exactly where this matters. A standard encoder pretrained on ImageNet learns
to classify objects ("is this a dog?"); DINOv2 learns to compare and contrast visual
regions, which is a better starting point for detecting faint structural signatures.

### How to get it

DINOv2 is hosted on [Hugging Face](https://huggingface.co/facebook/dinov2-base). You do
not need to download it manually — `timm` fetches the weights automatically on first use
once you have run `pip install -e ".[dev]"`.

---

## Model Inference

### Current: Python / PyTorch

The `predict.py` script runs sliding-window inference (a tile-by-tile scan across the
full image, stitching results back together) over full GeoTIFFs in Python using PyTorch
directly. This is the correct starting point — fast to iterate on, easy to debug, and
shares code with the training loop. It is not the target deployment runtime.

### Target: ONNX export → Rust

Once the model is trained and validated, the intended inference path is:

**Step 1 — Export to ONNX**

PyTorch models can be exported to [ONNX](https://onnx.ai/) (Open Neural Network Exchange),
a standardised format that decouples the model definition from the runtime. One export
command in Python produces a `.onnx` file that any compliant runtime can execute.

```python
torch.onnx.export(model, example_input, "sitescan.onnx", opset_version=17)
```

**Step 2 — Rust inference with `ort`**

[`ort`](https://github.com/pykeio/ort) is the Rust binding for
[ONNX Runtime](https://onnxruntime.ai/), Microsoft's production inference engine.
It supports CPU, CUDA (NVIDIA GPU), CoreML (Apple Silicon), and TensorRT as hardware
backends — you select which one at runtime without changing code. This is the recommended
Rust path for models with complex architectures like DINOv2.

```toml
# Cargo.toml
ort = { version = "2", features = ["cuda"] }
```

Alternative: [`tract`](https://github.com/sonos/tract) is a pure-Rust ONNX runtime
with zero native dependencies — simpler to deploy but CPU-only and may not support all
operations the model uses. Evaluate after export.

**Step 3 — GeoTIFF I/O with the `gdal` crate**

The [`gdal`](https://github.com/georust/gdal) crate wraps GDAL and handles reading
georeferenced rasters and writing probability maps back as GeoTIFF with the original
coordinate system and geographic position metadata preserved. This is a hard requirement
— the output map needs to align with basemap layers for archaeologists to review it.

**Step 4 — Parallel tile batching with `rayon`**

Sliding-window inference over a large Sentinel-2 scene generates thousands of 512×512
tiles. [`rayon`](https://github.com/rayon-rs/rayon) provides data-parallel iterators
in Rust with no async complexity — tiles are processed across CPU cores with a single
`.par_iter()` call, and results are assembled into the output raster in order.

### GPU optimisation

For GPU inference, two paths are available:

- **ONNX Runtime CUDA execution provider** (via `ort`): minimal friction, runs the
  exported model on GPU without modification.
- **TensorRT**: NVIDIA's inference optimizer. Accepts the ONNX model and compiles it
  into an engine tuned for the specific GPU — merging layers and optimising memory layout.
  Typically 2–4× faster than plain ONNX Runtime on NVIDIA hardware, at the cost of a
  per-GPU compilation step that takes a few minutes on first run.

### Quantization

The trained model uses 32-bit floats by default. FP16 (half-precision, 16-bit) inference
halves memory bandwidth and runs natively fast on any GPU from the last five years, with
negligible accuracy loss for segmentation outputs. INT8 (8-bit integers) gives a further
speedup but requires running a small sample of images through the model first so the
runtime can learn the typical range of values and compress them accurately — this should
be validated against the held-out test set before use.

Both are supported by ONNX Runtime and TensorRT without retraining.

---

## Data Strategy

### Input imagery: Sentinel-2

[Sentinel-2](https://sentinel.esa.int/web/sentinel/missions/sentinel-2) is a pair of
satellites operated by the European Space Agency (ESA) as part of the
[Copernicus Programme](https://www.copernicus.eu/). They provide free, open-access,
global multispectral imagery at 10-metre ground resolution on a 5-day revisit cycle.
Imagery is downloaded from the
[Copernicus Data Space](https://dataspace.copernicus.eu/) or processed directly in
[Google Earth Engine](https://earthengine.google.com/).

Four raw bands are used: Red (B04), Green (B03), Blue (B02), and Near-Infrared (B08).

A single image captures one moment in time. Cloud cover, seasonal variation, and
transient stress events introduce noise. To address this, two seasonal composites are
produced per site using Google Earth Engine, then exported as a single 11-channel GeoTIFF:

| Channel | Content |
|---------|---------|
| 0–3 | Red, Green, Blue, NIR — **dry season** median composite |
| 4 | NDVI — dry season |
| 5–8 | Red, Green, Blue, NIR — **wet season** median composite |
| 9 | NDVI — wet season |
| 10 | NDVI anomaly (dry NDVI − wet NDVI) |

NDVI (Normalized Difference Vegetation Index) is a standard remote sensing measure of
vegetation health, defined as `(NIR − Red) / (NIR + Red)` — first described by
[Tucker (1979)](https://doi.org/10.1016/0034-4257(79)90013-0). Values near 1.0 indicate
dense healthy vegetation; values near 0 indicate bare soil or stressed canopy.

The NDVI anomaly channel is the strongest single indicator of structural interference.
Healthy vegetation that is stressed in the dry season recovers in the wet season —
NDVI returns to baseline. Vegetation stressed by buried structures does not fully recover
because the constraint (impeded drainage, shallow soil over stone) is permanent. Persistent
stress that appears in the anomaly channel and holds linear geometry is the target signal.

The temporal window used for each composite (3 months, 5 months, full season) is treated
as a hyperparameter — a configuration choice that is not learned by the model but tuned
by running controlled experiments. Each window configuration will be trained and evaluated
separately, and the one that produces the lowest false positive rate is selected.

### Labels: binary masks from LiDAR ground truth

Training masks are derived from LiDAR surveys of confirmed sites. Each pixel is labelled
1 if it spatially overlaps a confirmed structure footprint (from GPS coordinates and
survey polygons), 0 otherwise. This is the honest ground truth: structures confirmed by
independent methods, not by the model itself.

LiDAR data is sourced from [OpenTopography](https://opentopography.org/), a NSF-funded
facility providing open access to high-resolution topographic datasets. For Bolivia,
confirmed structure coordinates are taken from the supplementary materials of
[Prümers et al. (2022)](https://doi.org/10.1038/s41586-022-04780-4).

**Future direction**: LiDAR is currently used only to generate training labels. Where
survey coverage is available, LiDAR-derived canopy height or terrain anomaly channels
could be incorporated as additional model inputs — providing a direct structural signal
that does not depend on the indirect vegetation stress proxy. This is not in scope for v1.

### Tiling

Source GeoTIFFs are chipped into 512×512 pixel tiles with 128-pixel overlap between
adjacent tiles. The overlap ensures that structures near tile edges appear fully in at
least one tile. Tiles are split into train / validation / test sets (80 / 15 / 5) with
a fixed random seed for reproducibility.

---

## Geographic Area: Casarabe Culture, Bolivia

**Target region**: Llanos de Mojos, Beni Department, Bolivia  
**Culture**: Casarabe (500–1400 CE)  
**Ground truth source**: [Prümers et al. (2022)](https://doi.org/10.1038/s41586-022-04780-4), *Nature* — GPS coordinates of confirmed
sites published in open-access supplementary materials

Bolivia's dry season (May–October) provides the longest windows of cloud-free Sentinel-2
imagery available anywhere in tropical South America. Cloud cover is the primary practical
constraint on usable imagery, and Bolivia minimises it.

The 2022 *Nature* paper on the Casarabe culture is open-access and includes precise GPS
coordinates of previously unknown monumental sites identified by LiDAR survey. This
provides high-quality, independently verified ground truth without requiring new fieldwork
or data agreements.

**Caveat on v1 scope**: The Llanos de Mojos is savanna-forest mosaic, not closed-canopy
rainforest. The canopy stress signal is cleaner here than in denser forest, making it a
stronger candidate for a first working system. The intended long-term target is closed
rainforest (PACUNAM LiDAR Initiative sites in Guatemala), where the same structural
interference mechanism operates but the signal is weaker and noisier. Validating the
pipeline on Bolivia first, then transferring to Guatemala, is the intended progression.

---

## Repository Structure

```
configs/           # model and training hyperparameters (edit here, not in code)
data/
  raw/             # source GeoTIFFs — not committed
  tiles/           # chipped 512×512 training patches
  annotations/     # binary masks matching tile filenames
src/
  dataset.py       # PyTorch Dataset and dataloader builder
  model.py         # model factory (smp wrappers, loads from model.yaml)
  train.py         # Lightning training loop
  predict.py       # sliding-window inference on full GeoTIFFs
  utils/
    tiling.py      # chip source GeoTIFFs into overlapping tiles
    transforms.py  # albumentations augmentation pipelines
    viz.py         # overlay predictions on RGB imagery
notebooks/         # EDA and result inspection
```

## Quickstart

```bash
pip install -e ".[dev]"

# chip raw imagery
python -m src.utils.tiling data/raw/site_001.tif

# train
python -m src.train --train-cfg configs/train.yaml --model-cfg configs/model.yaml

# predict on a new image
python -m src.predict path/to/image.tif checkpoints/best.ckpt
```

---

## References

**Ground truth and study areas**
- Prümers, H., Betancourt, C.J., Iriarte, J., Robinson, M., & Schaich, M. (2022). LiDAR reveals pre-Hispanic low-density urbanism in the Bolivian Amazon. *Nature*, 606, 325–328. https://doi.org/10.1038/s41586-022-04780-4
- Canuto, M.A. et al. (2018). Ancient lowland Maya complexity as revealed by airborne laser scanning of northern Guatemala. *Science*, 361(6409). https://doi.org/10.1126/science.aau0137

**Spectral indices**
- Tucker, C.J. (1979). Red and photographic infrared linear combinations for monitoring vegetation. *Remote Sensing of Environment*, 8(2), 127–150. https://doi.org/10.1016/0034-4257(79)90013-0

**Model**
- Oquab, M. et al. (2023). DINOv2: Learning Robust Visual Features without Supervision. *arXiv*. https://arxiv.org/abs/2304.07193
- Iakubovskii, P. (2019). Segmentation Models PyTorch. https://github.com/qubvel-org/segmentation_models.pytorch

**Data sources**
- ESA Sentinel-2 mission: https://sentinel.esa.int/web/sentinel/missions/sentinel-2
- Copernicus Data Space Ecosystem: https://dataspace.copernicus.eu/
- Google Earth Engine: https://earthengine.google.com/
- OpenTopography: https://opentopography.org/

**Inference**
- ONNX Runtime: https://onnxruntime.ai/
- ort (Rust ONNX Runtime bindings): https://github.com/pykeio/ort
- tract (pure-Rust ONNX runtime): https://github.com/sonos/tract
- gdal (Rust GeoTIFF / raster I/O): https://github.com/georust/gdal
- rayon (Rust data parallelism): https://github.com/rayon-rs/rayon

---

## License

[MIT](LICENSE)
