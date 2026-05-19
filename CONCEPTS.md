# Concepts Reference — sitescan

A study guide ordered by the product pipeline: from raw satellite data in, to probability
map out. Each section covers what you need to understand before the next one makes sense.

---

## 1. What satellite imagery actually is

A photograph records light intensity across three channels (RGB) as seen by a camera lens.
A satellite image is different: it records reflected electromagnetic radiation across many
wavelength ranges (bands), some of which are invisible to the human eye. Each band is a
separate greyscale image. Stacked together they form a multi-band raster.

What you're measuring is *reflectance* — the fraction of incoming sunlight that bounces
back off a surface into the sensor. Different materials have characteristic reflectance
profiles across wavelengths. Vegetation, bare soil, water, and stressed canopy each have
a distinct "spectral fingerprint". The model learns to read those fingerprints.

**Learn more**
- [NASA Earthdata: What is Remote Sensing?](https://www.earthdata.nasa.gov/learn/backgrounders/remote-sensing)
- [ESA: Electromagnetic Spectrum and Remote Sensing](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2)

---

## 2. Sentinel-2 and its bands

Sentinel-2 is an ESA satellite constellation (two satellites, 5-day revisit) that images
the entire Earth surface in 13 spectral bands at 10–60 metre resolution. It is free and
open access.

The bands most relevant to this project:

| Band | Wavelength | Resolution | What it captures |
|------|-----------|------------|-----------------|
| B02 | 490nm (Blue) | 10m | Atmospheric scatter, water |
| B03 | 560nm (Green) | 10m | Peak vegetation reflectance |
| B04 | 665nm (Red) | 10m | Chlorophyll absorption |
| B05 | 705nm (Red-Edge 1) | 20m | Chlorophyll transition zone |
| B06 | 740nm (Red-Edge 2) | 20m | Chlorophyll transition zone |
| B07 | 783nm (Red-Edge 3) | 20m | Chlorophyll transition zone |
| B08 | 833nm (NIR) | 10m | Vegetation structure |

The Red-Edge bands (B05–B07) are the distinguishing feature of Sentinel-2 versus older
sensors. Most consumer satellites and early satellite programmes only had RGB + NIR.

**Learn more**
- [Sentinel-2 Band Combinations](https://gisgeography.com/sentinel-2-bands-combinations/)
- [ESA Sentinel-2 User Guide](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi)

---

## 3. GeoTIFF and geospatial data formats

A GeoTIFF is a standard image format (TIFF) with geographic metadata embedded: which
coordinate reference system (CRS) the image uses, and the exact real-world location and
scale of each pixel. This is what lets you overlay the image on a map in QGIS or Google
Earth and have it land in the right place.

A **raster** is any grid of values tied to geographic space — a satellite image, a DEM,
a prediction map. A **vector** is geographic data stored as points, lines, or polygons
(GPS coordinates, survey boundaries). Training labels start as vectors (confirmed
structure polygons) and are rasterized (burned into a pixel grid) to match the imagery.

**CRS** (Coordinate Reference System): the mathematical model that maps points on Earth's
curved surface to flat 2D coordinates. Most satellite imagery uses UTM zones (metres
from a local origin) or WGS84 (latitude/longitude). The output probability map must share
the CRS of the input — otherwise it won't align with basemaps.

**Learn more**
- [QGIS: Introduction to GIS Concepts](https://docs.qgis.org/latest/en/docs/gentle_gis_introduction/)
- [Rasterio documentation](https://rasterio.readthedocs.io/) — the Python library used here for all raster I/O

---

## 4. How vegetation interacts with light

Plants absorb red light (B04) for photosynthesis and reflect NIR (B08) because their
cell structure scatters it. A healthy, chlorophyll-rich leaf: low red reflectance, high
NIR reflectance. A stressed or dying leaf: red reflectance rises (less absorption), NIR
reflectance falls (cell structure breaks down). This is the physical basis of every
vegetation index.

The **Red-Edge** (~700–750nm) is the steep transition slope between the red absorption
valley and the NIR plateau. It is extremely sensitive to small chlorophyll changes —
a 5% chlorophyll reduction produces a measurable shift in Red-Edge reflectance while
producing almost no measurable change in standard red/NIR reflectance.

**Learn more**
- [NASA: Vegetation and the Electromagnetic Spectrum](https://earthobservatory.nasa.gov/features/MeasuringVegetation)

---

## 5. Vegetation indices (NDVI and NDRE)

A vegetation index is a ratio calculated from two or more spectral bands that amplifies
the contrast between vegetation states and suppresses noise from illumination and
atmospheric effects.

**NDVI** (Normalized Difference Vegetation Index):
```
NDVI = (NIR − Red) / (NIR + Red)
```
Range: −1 to 1. Dense healthy vegetation: ~0.8. Bare soil: ~0.1. Water: negative.

**The saturation problem**: in dense tropical forest, NDVI approaches its upper limit.
Nearly all red light is absorbed; NIR reflectance is near-maximum. The index has no
headroom to detect a small stress-induced decline. It's clipped.

**NDRE** (Normalized Difference Red Edge):
```
NDRE = (NIR − RedEdge) / (NIR + RedEdge)     [using B06 at 740nm]
```
Because Red-Edge reflectance is more responsive to chlorophyll variation, NDRE retains
dynamic range in dense canopy. The same structural stress that goes invisible in NDVI
produces a measurable NDRE depression.

**Anomaly channel**: `dry NDRE − wet NDRE`. Healthy vegetation stressed in the dry season
recovers when the wet season arrives. Vegetation constrained by buried structures — where
drainage is permanently impeded by stone — does not fully recover. The anomaly channel
isolates that persistent, non-recovering stress.

**Learn more**
- Tucker (1979) — original NDVI paper: https://doi.org/10.1016/0034-4257(79)90013-0
- Gitelson & Merzlyak (1994) — Red-Edge sensitivity: foundational NDRE context
- [EOS: NDRE vs NDVI explained](https://eos.com/make-an-analysis/ndre/)

---

## 6. Seasonal compositing

A single satellite pass captures one moment — clouds, smoke, transient drought, and
sensor artefacts introduce noise. A **composite** collapses many images over a time
window into a single representative image, typically using the median pixel value at
each location. Outliers (clouds, shadows) average out.

Two composites are produced per site: **dry season** (May–Oct in Bolivia) and
**wet season** (Nov–Apr). The difference between them reveals which stress is seasonal
(drought, normal dry-down) versus persistent (structural interference).

The temporal window — how many months to include in each composite — is a **hyperparameter**:
a configuration choice that is not learned from data but tuned by running experiments and
measuring which setting produces the best results. This project will test 3-month,
5-month, and full-season windows.

**Learn more**
- [Google Earth Engine: Image Collections and Compositing](https://developers.google.com/earth-engine/guides/ic_composite_mosaic)

---

## 7. Terrain data (DEMs, Slope, TPI)

A **DEM** (Digital Elevation Model) is a raster where each pixel value is the terrain
elevation at that location, in metres. From a DEM you can derive:

**Slope**: the steepness of the terrain at each pixel, in degrees. High slope is a
natural cause of vegetation stress and soil drainage change — the model needs to know
this so it doesn't confuse hillside stress with structural stress.

**TPI** (Topographic Position Index): the elevation of each pixel minus the average
elevation of its neighbourhood. Positive = elevated relative to surroundings (ridge,
mound). Negative = lower than surroundings (valley, basin). Near-zero on sloped terrain
suggests a locally flat platform — a geometric signature of anthropogenic construction.

This project uses the **ALOS PALSAR 12.5m DEM** (from JAXA, distributed via the Alaska
Satellite Facility), or the **Copernicus 30m DEM** as a fallback. Both are processed in
Google Earth Engine before being stacked with the spectral channels.

**Learn more**
- [OpenTopography: Understanding DEMs](https://opentopography.org/)
- [ESRI: Topographic Position Index](https://www.esri.com/about/newsroom/arcuser/topographic-position-index/)
- [Alaska Satellite Facility: ALOS PALSAR](https://asf.alaska.edu/data-sets/sar-data-sets/alos-palsar/)

---

## 8. Supervised machine learning

The core pattern: you have labelled examples (input → known output), and you train a
model by showing it examples, measuring how wrong its predictions are, and adjusting its
internal parameters to be less wrong next time. Repeat across thousands of examples until
the model generalises.

The components:
- **Parameters** (weights): millions of numbers internal to the model. They start random
  and are adjusted by training. They are what gets "saved" in a checkpoint file.
- **Loss function**: the error signal. A single number measuring how wrong the model's
  prediction was on a batch of examples. Training minimises this number.
- **Optimiser**: the algorithm that adjusts the weights given the loss. AdamW is used
  here — a well-tested default for vision models.
- **Epoch**: one full pass through the entire training dataset. Training runs for many
  epochs, typically stopping when the model stops improving on held-out data.

Analogy: gradient descent (the underlying mechanism) is like rolling a ball downhill on
an error surface. Each training step nudges the weights slightly in the direction that
reduces error. The learning rate controls step size — too large and you overshoot, too
small and you never converge.

**Learn more**
- [3Blue1Brown: Neural Networks series](https://www.3blue1brown.com/topics/neural-networks) — best visual intuition available
- [fast.ai Practical Deep Learning](https://course.fast.ai/) — top-down, code-first approach

---

## 9. Train / validation / test splits

You cannot evaluate a model on the same data it trained on — it will have memorised
the examples. Three separate, non-overlapping subsets of the data serve different
purposes:

- **Train** (80%): the model sees this data and learns from it.
- **Validation** (15%): the model never trains on this, but it's checked against it
  after every epoch. Used to detect overfitting and to pick the best checkpoint.
- **Test** (5%): held completely aside until training is finished. The final, honest
  evaluation of whether the model generalises to unseen data.

**Overfitting**: when a model performs well on training data but poorly on new data — it
has memorised examples rather than learned the underlying pattern. Equivalent to a system
that works perfectly on your dev cluster and fails in production because it tuned to
specific noise rather than the actual signal.

---

## 10. Neural network architecture basics

A neural network is a stack of layers. Each layer transforms its input into a new
representation through matrix multiplication and a non-linear activation function.
Deep networks stack many such layers — each one learns increasingly abstract features
(edges → textures → shapes → semantic patterns).

For images, **convolutional layers** (CNNs) are the standard building block. Rather
than connecting every pixel to every neuron (prohibitively expensive), a small filter
slides across the image and learns local patterns — the same filter detects an edge
wherever it appears, regardless of position.

**Learn more**
- [CS231n: Convolutional Neural Networks for Visual Recognition](https://cs231n.stanford.edu/) — the standard course, freely available

---

## 11. Image segmentation

Three levels of difficulty in computer vision tasks:

- **Classification**: what is in this image? (one label per image)
- **Object detection**: where are the objects? (bounding boxes)
- **Semantic segmentation**: label every pixel with a category

Segmentation is the hardest and most informative — you get a full map, not just a
bounding box or a yes/no answer.

**Binary segmentation** is the simplest case: each pixel gets either 0 (background) or
1 (target class). The output is a mask. In this project: structure pixels are 1,
everything else is 0.

---

## 12. UNet architecture

UNet was designed specifically for segmentation tasks where training data is limited
(it was originally developed for medical imaging). Its structure:

```
Input image
    ↓
Encoder (downsampling path)
  Block 1: features at full resolution  ──────────────────────┐ skip
  Block 2: features at 1/2 resolution   ─────────────────┐    │
  Block 3: features at 1/4 resolution   ────────────┐    │    │
  Bottleneck: most compressed representation        │    │    │
  Block 4: upsample to 1/4              ←───────────┘    │    │
  Block 5: upsample to 1/2             ←────────────────┘    │
  Block 6: upsample to full resolution ←─────────────────────┘
    ↓
Output mask (same size as input)
```

**Skip connections** pass the feature maps from each encoder block directly to the
corresponding decoder block. The decoder uses these to recover fine spatial detail that
would otherwise be lost in the compression. Without them, the output mask would be
blurry — you'd lose the sharp edges that define the exact boundary of a structure.

**Learn more**
- [Original UNet paper (Ronneberger et al., 2015)](https://arxiv.org/abs/1505.04597) — short and readable

---

## 13. Transfer learning and pretraining

Training a vision model from random weights requires enormous amounts of labelled data.
This project will have hundreds of labelled tiles at best. Transfer learning sidesteps
this: start with a model already trained on a large dataset for a different task, then
fine-tune it on your small dataset.

The pretrained model's weights encode general visual knowledge (edges, textures, colour
gradients, shapes). Fine-tuning adjusts them for the specific patterns in your data
without discarding that foundation. The less data you have, the more valuable a good
pretrained starting point is.

**Self-supervised pretraining** (DINOv2): instead of training on human-labelled data,
the model is trained by generating its own supervision signal — comparing different crops
and views of the same image and learning to produce similar representations for related
patches. This lets you train on 142 million images without needing anyone to label them.

**Learn more**
- [DINOv2 paper](https://arxiv.org/abs/2304.07193)
- [fast.ai: Transfer learning](https://course.fast.ai/Lessons/lesson1.html) — covered in lesson 1

---

## 14. Class imbalance and loss functions

In this dataset, buried structure pixels make up roughly 1–3% of any tile. A model that
always predicts "background" would be 97–99% accurate — and completely worthless. This
is the **class imbalance** problem.

Two loss functions are combined to address it:

**Binary Cross-Entropy (BCE)**: the standard loss for binary classification. Penalises
each pixel independently. Without a correction, it will optimise for overall pixel
accuracy, which the all-background strategy maximises.

**Dice loss**: measures the overlap between predicted and actual mask regions as a
fraction. If the model predicts no structure at all, the overlap is zero and the loss is
maximum — it cannot cheat by predicting all background. Purpose-built for imbalanced
segmentation.

**pos_weight**: an additional penalty multiplier on structure pixels in the BCE term.
Set to 8.0 — a missed structure pixel costs 8× more than a missed background pixel.
Tune up if the model misses structures; tune down if it produces too many false alarms.

**Learn more**
- [StatQuest: Cross Entropy](https://www.youtube.com/@statquest) — search "cross entropy StatQuest"
- [Dice loss explained](https://arxiv.org/abs/1707.03237) — V-Net paper, section 3

---

## 15. Evaluation metrics

**IoU** (Intersection over Union), also called Jaccard Index:
```
IoU = (predicted ∩ ground truth) / (predicted ∪ ground truth)
```
0 = no overlap. 1 = perfect match. It is the standard metric for segmentation. A model
that predicts a slightly larger or offset region gets partial credit — unlike pixel
accuracy, which gives full credit for getting the background right.

**Precision**: of all the pixels the model flagged as structure, what fraction actually
were? High precision = few false alarms.

**Recall**: of all the actual structure pixels, what fraction did the model find? High
recall = few missed structures.

The tradeoff between them is controlled by the detection threshold. At threshold 0.5,
every pixel scoring above 0.5 is called a structure. Lowering the threshold increases
recall (find more structures) at the cost of precision (more false alarms). The right
threshold depends on whether a missed site or a false alarm is costlier.

**Learn more**
- [StatQuest: Precision and Recall](https://www.youtube.com/@statquest)

---

## 16. Inference vs training

**Training**: iterative, GPU-intensive, runs once (or a few times during development).
Weights are updated constantly. Requires the full training framework.

**Inference**: a single forward pass through a frozen model. Weights don't change.
This is what runs in production — on new, unlabelled imagery. The goal is to make it as
fast and lightweight as possible.

ONNX decouples the model definition (PyTorch) from the inference runtime. Once exported,
the `.onnx` file can be run by any compliant runtime without PyTorch installed.

**Quantization** reduces the numerical precision of the model weights and activations:
- **FP32** (default): 32-bit floats. Full precision.
- **FP16**: 16-bit floats. Half the memory, natively fast on modern GPUs. Negligible
  accuracy loss for segmentation.
- **INT8**: 8-bit integers. Further speedup, requires calibration (a small sample run
  that characterises the typical value ranges before compressing them).

---

## 17. Zero-shot anomaly detection

When you have no labelled training data for a new region, supervised segmentation is not
possible. Zero-shot anomaly detection is the alternative.

DINOv2 acts as a feature extractor: it converts each image patch into a high-dimensional
vector (a "fingerprint"). In a uniform, healthy forest, patches of similar vegetation
produce similar vectors — they cluster tightly in feature space. A patch above a buried
structure has a subtly different spectral and spatial signature — it doesn't cluster with
its neighbours. It's a statistical outlier.

You characterise the "normal" distribution (healthy surrounding forest), then flag patches
that deviate beyond a threshold. No labelled examples of buried structures are needed.

The limitation: it flags anything unusual — disease, logging edges, burned areas, natural
clearings. It produces candidates for human review, not ground truth. It is a triage tool
for unsurveyed regions, not a replacement for the supervised model in regions where
training data exists.

**Learn more**
- [Anomalib: Industrial anomaly detection library](https://github.com/openvinotoolkit/anomalib) — includes DINOv2-based methods
- [PatchCore paper](https://arxiv.org/abs/2106.08265) — the most practical zero-shot anomaly detection approach

---

## 18. What the first smoke run did

The first implementation pass used **Fazenda Colorada**, a known geoglyph site in Acre,
Brazil, as a real end-to-end test case. The point was not to produce a useful
archaeological model yet. The point was to prove that the data pipeline can move from
public geospatial sources to model output without breaking georeferencing.

The workflow:

1. **Export imagery from Earth Engine**
   - Source: Sentinel-2 surface reflectance plus Copernicus DEM.
   - Output: a 13-channel GeoTIFF in `EPSG:32719`.
   - Channels: dry RGB/NIR/NDRE, wet RGB/NIR/NDRE, NDRE anomaly, slope, TPI.

2. **Extract candidate labels**
   - Source: Amazon Geoglyphs KML linework.
   - Output: a Fazenda Colorada GeoJSON with point and line features near the site.

3. **Rasterize labels**
   - The vector labels were burned into a binary mask aligned exactly to the exported
     GeoTIFF.
   - The first mask had 1,134 positive pixels.

4. **Prepare tiles**
   - The first export was 451 x 492 pixels, so 256-pixel tiles were used.
   - Nine overlapping image/mask tiles were generated.

5. **Train a smoke model**
   - A small UNet with a randomly initialized ResNet-18 encoder trained for one CPU epoch.
   - The model was deliberately weak; it existed to test the plumbing.

6. **Predict and evaluate**
   - Sliding-window prediction wrote a georeferenced probability GeoTIFF.
   - A threshold sweep computed IoU, precision, recall, and F1.

Important lesson: a successful smoke run means "the system runs", not "the model works".
The first IoU was near zero, which is expected from one site, candidate labels, a random
small model, and one epoch of CPU training.

---

## 19. Data quality lessons from the smoke run

**NaNs in satellite composites**: cloud and scene masks can leave missing pixels in the
exported GeoTIFF. If those NaNs reach PyTorch, the loss becomes NaN and training fails.
The loader now replaces NaNs with zero as a defensive measure, but a better next step is
to clean or flag nodata during preprocessing.

**Candidate labels are not ground truth yet**: KML linework is useful, but it must be
reviewed. Some features are points, some are duplicate lines, and some are approximate
outlines. Before trusting model metrics, inspect the raster, vectors, and mask together
in QGIS.

**Tile size must match export size**: the default 512-pixel tile assumes a larger raster.
The first Fazenda Colorada export was smaller, so 256-pixel tiles were used. For real
experiments, either export a larger area or set tile size intentionally.

**Positive-only tiles are misleading**: all nine first-pass tiles contained positive
label pixels because the AOI was tight around the known site. A useful model needs
negative/background context too, otherwise it cannot learn what ordinary landscape looks
like.

**CPU training is only for plumbing**: the Intel Mac mini can verify the loop with a
small model, but DINOv2 and serious segmentation experiments should wait for a stronger
machine or a smaller controlled experiment config.

---

## Appendix: tools in this project

| Tool | Role | Docs |
|------|------|------|
| Google Earth Engine | Compositing, terrain derivatives, export | https://developers.google.com/earth-engine |
| rasterio | GeoTIFF I/O in Python | https://rasterio.readthedocs.io |
| PyTorch | Model definition and training | https://pytorch.org/docs |
| segmentation-models-pytorch | UNet + encoder wiring | https://github.com/qubvel-org/segmentation_models.pytorch |
| timm | DINOv2 weights | https://github.com/huggingface/pytorch-image-models |
| Lightning | Training loop scaffolding | https://lightning.ai/docs |
| albumentations | Image augmentation | https://albumentations.ai/docs |
| QGIS | Visualising GeoTIFFs and outputs | https://qgis.org |
| ONNX Runtime / ort | Production inference | https://onnxruntime.ai |
