import math
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from shapely.ops import unary_union, polygonize
from tidyzoning import find_district_idx
from tqdm import tqdm  

def generate_parcel_info(tidyparcel, tidyzoning):
    """
    Generates parcel-level lot dimension info and joins with zoning district index.

    Parameters:
    tidyparcel (GeoDataFrame): Must include 'parcel_id', 'Prop_ID', 'parcel_label', 'geometry', 'side'
    tidyzoning (GeoDataFrame): Must include polygon geometries

    Returns:
    DataFrame with one row per parcel, including:
        - Prop_ID, parcel_id, Parcel_label
        - lot_width, lot_depth, lot_area
        - zoning_id (index of tidyzoning that contains centroid of parcel)
    """
    records = []
    
    find_district_idx_results = find_district_idx(tidyparcel, tidyzoning)

    # calculating the lot width, lot depth and lot area for each parcel with corresponding zoning id
    for parcel_id, group in tqdm(tidyparcel.groupby("parcel_id"), desc="Processing parcels"):
        Prop_ID = group['Prop_ID'].iloc[0]
        Parcel_label = group['parcel_label'].iloc[0]

        # Get zoning index if available
        zoning_row = find_district_idx_results[find_district_idx_results['parcel_id'] == parcel_id]
        zoning_id = zoning_row['zoning_id'].iloc[0] if not zoning_row.empty else None

        # Front and rear points
        front = group[(group["side"] == "front") | (group["side"] == "rear")]
        side = group[(group["side"] == "Interior side") | (group["side"] == "Exterior side")]
        no_centroids_rows = group[(group['side'].notna()) & (group['side'] != "centroid")]

        if front.empty or side.empty:
            records.append({
                "Prop_ID": Prop_ID,
                "parcel_id": parcel_id,
                "Parcel_label": Parcel_label,
                "lot_depth": None,
                "lot_width": None,
                "lot_area": None,
                "zoning_id": zoning_id
            })
            continue

        # Compute lot depth & angle
        lot_width = (front.geometry.length * 3.28084).max()  # convert m to ft
        lot_depth = (side.geometry.length * 3.28084).max()  # convert m to ft

        # Compute lot area using polygonized edges (without centroids)
        polygons = polygonize(unary_union(no_centroids_rows.geometry))
        lot_polygon = unary_union(polygons)
        lot_area = lot_polygon.area / 4046.8564224  # convert m² to acre

        records.append({
            "Prop_ID": Prop_ID,
            "parcel_id": parcel_id,
            "Parcel_label": Parcel_label,
            "lot_width": lot_width,
            "lot_depth": lot_depth,
            "lot_area": lot_area,
            "zoning_id": zoning_id
        })

    # Drop rows where any key value is missing, then reset index
    df = pd.DataFrame(records)
    df = df.dropna(subset=["lot_width", "lot_depth", "lot_area"]).reset_index(drop=True)
    return df
