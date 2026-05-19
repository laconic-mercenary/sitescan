# Data Sources

This project starts with one real archaeological site: Fazenda Colorada in Acre, Brazil.
The goal is a reproducible imagery-plus-label workflow before trying to generalize.

## 1. Vector Labels

Preferred source:

- Mendeley Data: `Amazon Geoglyphs`
- DOI: `10.17632/5ynjwk7gc7.1`
- URL: <https://data.mendeley.com/datasets/5ynjwk7gc7/1>
- License shown by Mendeley: CC BY 4.0

Download manually from the Mendeley page and place the extracted files under:

```bash
data/external/amazon_geoglyphs/mendeley_v1/
```

The live KML is useful for exploration, but prefer the archived Mendeley version for
training data provenance until live-file licensing is clarified:

```bash
data/external/amazon_geoglyphs/live/amazon_geoglyphs.kml
```

Fazenda Colorada candidate structures:

| KML id | Structure | Approx center |
|--------|-----------|---------------|
| `rbrci` | Rio Branco Circle 160m | `-9.872980, -67.534413` |
| `rbrsq` | Rio Branco Square 200m | `-9.875281, -67.534505` |
| `rbrdr` | Rio Branco Double Rectangle 147 x 138m | `-9.877652, -67.535332` |

## 2. Sentinel-2 Imagery

Use Google Earth Engine with:

```text
COPERNICUS/S2_SR_HARMONIZED
```

After authenticating and registering an Earth Engine project, run:

```bash
python scripts/export_fazenda_colorada_s2.py --project <your-earthengine-project-id>
```

Credentials note: local development uses the OAuth token created by:

```bash
earthengine authenticate
```

Do not paste API keys or secrets into this repo. Service-account credentials are only
needed later if exports are automated from CI or a server.

If you already ran `earthengine set_project <project-id>`, this should also work:

```bash
python scripts/export_fazenda_colorada_s2.py
```

If the command says the Earth Engine API is disabled, open the activation URL printed
in the error, enable `earthengine.googleapis.com` for the project, wait a few minutes,
then rerun the export.

If the command says the project is not registered to use Earth Engine, open:

```text
https://console.cloud.google.com/earth-engine/configuration?project=sitescan-main01
```

Register the project for Earth Engine access and complete the noncommercial eligibility
flow if Google asks for it.

Observed local project during setup:

```text
sitescan-main01
```

The script starts a Google Drive export into:

```text
sitescan_exports/fazenda_colorada_s2_13ch.tif
```

Download the exported GeoTIFF from Drive and place it at:

```bash
data/raw/fazenda_colorada/fazenda_colorada_s2_13ch.tif
```

Default export windows:

- Wet season: `2020-11-01` to `2021-04-30`
- Dry season: `2021-05-01` to `2021-10-31`

Default channels:

| Channel | Name |
|---------|------|
| 0 | `dry_red` |
| 1 | `dry_green` |
| 2 | `dry_blue` |
| 3 | `dry_nir` |
| 4 | `dry_ndre` |
| 5 | `wet_red` |
| 6 | `wet_green` |
| 7 | `wet_blue` |
| 8 | `wet_nir` |
| 9 | `wet_ndre` |
| 10 | `ndre_anomaly` |
| 11 | `slope` |
| 12 | `tpi` |

The export uses `EPSG:32719`, 10m scale, and a small buffered bounding box around the
three Fazenda Colorada structures.

## 3. Terrain

The Sentinel-2 export script includes terrain channels from:

```text
COPERNICUS/DEM/GLO30
```

It derives:

- `slope` with `ee.Terrain.slope`
- `tpi` as elevation minus 90m focal mean elevation

## 4. Label Rasterization

Extract the Fazenda Colorada candidate vectors from the local KML:

```bash
sitescan-extract-fazenda-labels
```

This writes:

```text
data/interim/fazenda_colorada/fazenda_colorada_vectors.geojson
```

After the Sentinel-2 GeoTIFF is downloaded from Google Drive, rasterize the labels:

```bash
sitescan-rasterize-labels \
  --vectors data/interim/fazenda_colorada/fazenda_colorada_vectors.geojson \
  --reference data/raw/fazenda_colorada/fazenda_colorada_s2_13ch.tif \
  --output data/interim/fazenda_colorada/fazenda_colorada_mask.tif
```

Then chip the aligned image and mask:

```bash
sitescan-prepare-tiles \
  --image data/raw/fazenda_colorada/fazenda_colorada_s2_13ch.tif \
  --mask data/interim/fazenda_colorada/fazenda_colorada_mask.tif \
  --output data/tiles/fazenda_colorada \
  --tile-size 256 \
  --overlap 64
```

The first Fazenda Colorada export is `451 x 492` pixels at 10m resolution, so it is
smaller than the default `512 x 512` training tile. Use `256` pixel tiles for this first
single-site dataset, or rerun the Earth Engine export with a larger buffer before using
the default training config.

Current local products:

```text
data/raw/fazenda_colorada/fazenda_colorada_s2_13ch.tif
data/interim/fazenda_colorada/fazenda_colorada_vectors.geojson
data/interim/fazenda_colorada/fazenda_colorada_mask.tif
data/tiles/fazenda_colorada/manifest.json
```

Current label raster result:

```text
positive mask pixels: 1134
tile count: 9
positive tiles: 9
```

## 5. Historical Context

Use Landsat Collection 2 Surface Reflectance through Earth Engine only for context at
first. Do not mix it into the 13-channel Sentinel-2 model input until the data contract
is intentionally changed.

Useful collections:

```text
LANDSAT/LT05/C02/T1_L2
LANDSAT/LE07/C02/T1_L2
LANDSAT/LC08/C02/T1_L2
LANDSAT/LC09/C02/T1_L2
```

## 6. Do Not Use For Training

Do not scrape or export Google Earth / Google Maps visual imagery for model training.
Use Google Earth only as a manual visual reference. Pull model inputs from Earth Engine
datasets with clear dataset provenance.
