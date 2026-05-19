"""Export a Fazenda Colorada Sentinel-2 training raster from Google Earth Engine."""

from __future__ import annotations

import argparse

import ee
from ee.ee_exception import EEException

FAZENDA_COLORADA_POINTS = [
    (-67.534413, -9.872980),
    (-67.534505, -9.875281),
    (-67.535332, -9.877652),
]

CLOUDY_PIXEL_PERCENTAGE = 40
EXPORT_SCALE_METERS = 10
EXPORT_CRS = "EPSG:32719"
DEFAULT_BUFFER_METERS = 2200
DEFAULT_DRIVE_FOLDER = "sitescan_exports"
DEFAULT_PREFIX = "fazenda_colorada_s2_13ch"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a dry/wet Sentinel-2 composite for Fazenda Colorada."
    )
    parser.add_argument(
        "--project",
        default=None,
        help=(
            "Google Cloud project registered for Earth Engine. "
            "Omit to use earthengine set_project."
        ),
    )
    parser.add_argument("--dry-start", default="2021-05-01")
    parser.add_argument("--dry-end", default="2021-10-31")
    parser.add_argument("--wet-start", default="2020-11-01")
    parser.add_argument("--wet-end", default="2021-04-30")
    parser.add_argument("--buffer-meters", type=int, default=DEFAULT_BUFFER_METERS)
    parser.add_argument("--drive-folder", default=DEFAULT_DRIVE_FOLDER)
    parser.add_argument("--file-prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--cloud-pct", type=int, default=CLOUDY_PIXEL_PERCENTAGE)
    return parser.parse_args()


def mask_sentinel2_clouds(image: ee.Image) -> ee.Image:
    scl = image.select("SCL")
    valid_scene = (
        scl.neq(0)
        .And(scl.neq(1))
        .And(scl.neq(3))
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
        .And(scl.neq(11))
    )
    return image.updateMask(valid_scene).divide(10000)


def build_site_region(buffer_meters: int) -> ee.Geometry:
    points = ee.Geometry.MultiPoint(FAZENDA_COLORADA_POINTS)
    return points.buffer(buffer_meters).bounds()


def build_sentinel2_composite(
    region: ee.Geometry,
    start_date: str,
    end_date: str,
    cloud_pct: int,
    prefix: str,
) -> ee.Image:
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", cloud_pct))
        .map(mask_sentinel2_clouds)
    )
    composite = collection.median()
    red = composite.select("B4").rename(f"{prefix}_red")
    green = composite.select("B3").rename(f"{prefix}_green")
    blue = composite.select("B2").rename(f"{prefix}_blue")
    nir = composite.select("B8").rename(f"{prefix}_nir")
    ndre = composite.normalizedDifference(["B8", "B6"]).rename(f"{prefix}_ndre")
    return ee.Image.cat([red, green, blue, nir, ndre]).toFloat()


def build_terrain(region: ee.Geometry) -> ee.Image:
    dem = ee.ImageCollection("COPERNICUS/DEM/GLO30").filterBounds(region).select("DEM").mosaic()
    slope = ee.Terrain.slope(dem).rename("slope")
    tpi = dem.subtract(dem.focal_mean(radius=90, units="meters")).rename("tpi")
    return ee.Image.cat([slope, tpi]).toFloat()


def build_export_image(args: argparse.Namespace) -> tuple[ee.Image, ee.Geometry]:
    region = build_site_region(args.buffer_meters)
    dry = build_sentinel2_composite(region, args.dry_start, args.dry_end, args.cloud_pct, "dry")
    wet = build_sentinel2_composite(region, args.wet_start, args.wet_end, args.cloud_pct, "wet")
    anomaly = dry.select("dry_ndre").subtract(wet.select("wet_ndre")).rename("ndre_anomaly")
    terrain = build_terrain(region)
    image = ee.Image.cat([dry, wet, anomaly, terrain]).clip(region).toFloat()
    return image, region


def main() -> None:
    args = parse_args()
    try:
        if args.project:
            ee.Initialize(project=args.project)
        else:
            ee.Initialize()
    except EEException as init_err:
        message = str(init_err)
        if "SERVICE_DISABLED" in message or "earthengine.googleapis.com" in message:
            print(
                "Earth Engine initialization failed because the API is disabled "
                "for this project."
            )
            print("Open the activation URL in the error below, enable the API, wait a few minutes,")
            print("then rerun this export command.")
        elif "not registered to use Earth Engine" in message:
            print("Earth Engine initialization failed because the project is not registered.")
            print("Open the Earth Engine configuration URL in the error below, register")
            print("the project for Earth Engine access, then rerun this export command.")
        raise

    image, region = build_export_image(args)
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=args.file_prefix,
        folder=args.drive_folder,
        fileNamePrefix=args.file_prefix,
        region=region,
        scale=EXPORT_SCALE_METERS,
        crs=EXPORT_CRS,
        maxPixels=1_000_000_000,
        fileFormat="GeoTIFF",
    )
    task.start()
    print(f"Started Earth Engine export: {task.id}")
    print(f"Google Drive folder: {args.drive_folder}")
    print(f"File prefix: {args.file_prefix}")


if __name__ == "__main__":
    main()
