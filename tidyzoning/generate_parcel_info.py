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
    # Define label categories
    confident_labels = [
        'regular inside parcel',
        'regular corner parcel',
        'special parcel_standard',
        'curve parcel_standard',
        'cul_de_sac parcel_standard',
        'no_match_address_standard',
        'no_address_parcel_standard'
    ]
    non_confident_labels = [
        'jagged parcel',
        'duplicated address',
        'cul_de_sac parcel_other',
        'special parcel_other',
        'no_match_address_other',
        'curve parcel_other',
        'no_address_parcel_other'
    ]

    records = []
    find_district_idx_results = find_district_idx(tidyparcel, tidyzoning)

    for parcel_id, group in tqdm(tidyparcel.groupby("parcel_id"), desc="Processing parcels"):
        Prop_ID = group['Prop_ID'].iloc[0]
        Parcel_label = group['parcel_label'].iloc[0]

        # Get zoning index if available
        zoning_row = find_district_idx_results[find_district_idx_results['parcel_id'] == parcel_id]
        zoning_id = zoning_row['zoning_id'].iloc[0] if not zoning_row.empty else None

        # Front/rear and side edges
        front = group[group["side"].isin(["front", "rear"])]
        side = group[group["side"].isin(["Interior side", "Exterior side"])]
        no_centroids_rows = group[(group['side'].notna()) & (group['side'] != "centroid")]

        # Compute lot area (in acres)
        polygons = polygonize(unary_union(no_centroids_rows.geometry))
        lot_polygon = unary_union(polygons)
        lot_area = lot_polygon.area / 4046.8564224

        # Compute width & depth based on label category
        if Parcel_label in confident_labels:
            if front.empty or side.empty:
                lot_width = None
                lot_depth = None
            else:
                lot_width = (front.geometry.length * 3.28084).max()
                lot_depth = (side.geometry.length * 3.28084).max()
        elif Parcel_label in non_confident_labels:
            lot_width = 1
            lot_depth = 1
        else:
            # Default: treat as confident
            if front.empty or side.empty:
                lot_width = None
                lot_depth = None
            else:
                lot_width = (front.geometry.length * 3.28084).max()
                lot_depth = (side.geometry.length * 3.28084).max()

        records.append({
            "Prop_ID": Prop_ID,
            "parcel_id": parcel_id,
            "Parcel_label": Parcel_label,
            "lot_width": lot_width,
            "lot_depth": lot_depth,
            "lot_area": lot_area,
            "zoning_id": zoning_id
        })

    # Drop rows where any key dimension is missing
    df = pd.DataFrame(records)
    # df = df.dropna(subset=["lot_width", "lot_depth", "lot_area"]).reset_index(drop=True)
    return df