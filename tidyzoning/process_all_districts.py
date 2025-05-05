import os
import glob
import json
import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping

def filter_parcels_by_district(
    tidyparcel_feeds, district_gdf,
    side_col="side", side_val="centroid",
    id_col="parcel_id"
):
    """
    Returns only those rows of tidyparcel_feeds whose 'centroid' points lie within district_gdf.
    """
    # 1) isolate centroid points
    centroids = tidyparcel_feeds[tidyparcel_feeds[side_col] == side_val].copy()
    # 2) ensure both GDFs use the same CRS
    district_gdf = district_gdf.dropna(subset=['geometry'])
    if district_gdf.crs != centroids.crs:
        district_gdf = district_gdf.to_crs(centroids.crs)
    # 3) spatial join: keep only centroids within the district polygons
    joined = gpd.sjoin(
        centroids, 
        district_gdf[["geometry"]], 
        how="inner",
        predicate="within"
    )
    # 4) grab the unique parcel_ids of those centroids
    valid_ids = joined[id_col].unique()
    # 5) return the full tidyparcel_feeds restricted to those IDs (in WGS84 for output)
    return tidyparcel_feeds[tidyparcel_feeds[id_col].isin(valid_ids)].to_crs("EPSG:4326").copy()

def write_geojson_dynamic(gdf, filepath, side_col='side', side_val='centroid'):
    """
    Export a GeoDataFrame to GeoJSON, dropping any property with a NaN value.
    """
    features = []
    for _, row in gdf.iterrows():
        geom = mapping(row.geometry)
        # include all non-null properties
        props = {
            k: v for k, v in row.drop(labels='geometry').to_dict().items()
            if pd.notnull(v)
        }
        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": props
        })
    feature_collection = {"type": "FeatureCollection", "features": features}
    with open(filepath, 'w') as f:
        json.dump(feature_collection, f)

def process_all_districts(
    tidyparcel_path, district_folder, output_folder,
    side_col="side", side_val="centroid", id_col="parcel_id"
):
    """
    For each district geojson in district_folder, filter parcels and write output geojson.
    Drops all NaN-valued properties in every feature.
    """
    tidyparcel_feeds = gpd.read_file(tidyparcel_path)
    os.makedirs(output_folder, exist_ok=True)
    for dist_fp in glob.glob(os.path.join(district_folder, "*.geojson")):
        name = os.path.splitext(os.path.basename(dist_fp))[0]
        district_gdf = gpd.read_file(dist_fp)
        valid_gdf = filter_parcels_by_district(
            tidyparcel_feeds, district_gdf,
            side_col=side_col, side_val=side_val, id_col=id_col
        )
        out_fp = os.path.join(output_folder, f"{name}_parcels.geojson")
        write_geojson_dynamic(valid_gdf, out_fp, side_col=side_col, side_val=side_val)
        print(f"Written {out_fp}")