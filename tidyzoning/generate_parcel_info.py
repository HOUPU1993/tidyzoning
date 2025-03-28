import math
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from shapely.ops import unary_union, polygonize
from shapely.affinity import rotate

def compute_angle(p1, p2):
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return math.degrees(math.atan2(dy, dx))

def generate_parcel_info(tidyparcel,tidyzoning):
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
    
    how to use:
    tidyparcel = generate_parcel_info(filtered_tidyparcel,tidyzoning)
    """
    
    records = []

    # Get zoning matches for centroids
    centroid_rows = tidyparcel[tidyparcel['side'] == 'centroid']
    if centroid_rows.empty:
        print("No centroids found in tidyparcel.")
        zoning_lookup = pd.DataFrame(columns=["prop_id", "parcel_id", "zoning_id"])
    else:
        joined = gpd.sjoin(centroid_rows, tidyzoning, how='left', predicate='within')
        zoning_lookup = pd.DataFrame({
            "prop_id": joined["Prop_ID"],
            "parcel_id": joined["parcel_id"],
            "zoning_id": joined["index_right"]
        })

    for parcel_id, group in tidyparcel.groupby("parcel_id"):
        Prop_ID = group['Prop_ID'].iloc[0]
        Parcel_label = group['parcel_label'].iloc[0]

        # Get zoning index if available
        zoning_row = zoning_lookup[zoning_lookup['parcel_id'] == parcel_id]
        zoning_id = zoning_row['zoning_id'].iloc[0] if not zoning_row.empty else None

        # Front and rear points
        front = group[group["side"] == "front"]
        rear = group[group["side"] == "rear"]
        no_centroids_rows = group[(group['side'].notna()) & (group['side'] != "centroid")]

        if front.empty or rear.empty:
            records.append({
                "Prop_ID": Prop_ID,
                "parcel_id": parcel_id,
                "Parcel_label": Parcel_label
                "lot_depth": None,
                "lot_width": None,
                "lot_area": None,
                "zoning_id": zoning_id
            })
            continue

        # Compute lot depth & angle
        front_centroid = front.geometry.centroid.unary_union.centroid
        rear_centroid = rear.geometry.centroid.unary_union.centroid
        lot_depth = front_centroid.distance(rear_centroid) * 3.28084 # convert m to ft
        angle = compute_angle(front_centroid, rear_centroid)

        # Rotate geometry to align depth
        full_geom = group.unary_union
        rotated = rotate(full_geom, -angle, origin='centroid', use_radians=False)
        minx, miny, maxx, maxy = rotated.bounds
        lot_width = abs(maxy - miny) * 3.28084  # width is perpendicular to depth, and convert m to ft

        # Compute lot area using polygonized edges (without centroids)        
        polygons = polygonize(unary_union(no_centroids_rows.geometry))
        lot_polygon = unary_union(polygons)
        lot_area = lot_polygon.area * 10.7639  # convert m² to ft²

        records.append({
            "Prop_ID": Prop_ID,
            "parcel_id": parcel_id,
            "Parcel_label": Parcel_label,
            "lot_width": lot_width,
            "lot_depth": lot_depth,
            "lot_area": lot_area,
            "zoning_id": zoning_id
        })

    return pd.DataFrame(records)