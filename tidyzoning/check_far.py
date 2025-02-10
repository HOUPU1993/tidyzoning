import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from tidyzoning import get_zoning_req

def check_far(tidybuilding, tidyzoning, tidyparcel):
    """
    Checks whether the Floor Area Ratio (FAR) of a given building complies with zoning constraints.

    Parameters:
    ----------
    tidybuilding : A GeoDataFrame containing information about a single building. 
    tidyparcel : A GeoDataFrame containing information about the tidyparcels(single/multiple ). 
    tidyzoning : A GeoDataFrame containing zoning constraints. It may have multiple rows,

    Returns:
    -------
    DataFrame
        A DataFrame with the following columns:
        - 'Prop_ID': Identifier for the property (from `tidyparcel`).
        - 'zoning_id': The index of the corresponding row from `tidyzoning`.
        - 'allowed': A boolean value indicating whether the building's FAR 
    """
    ureg = UnitRegistry()
    results = []

    # Calculate the floor area of the building
    if len(tidybuilding['floor_area']) == 1:
        fl_area = tidybuilding['floor_area'].iloc[0]
    elif len(tidybuilding['total_floors']) == 1:
        floors = tidybuilding['total_floors'].iloc[0]
        fl_area = tidybuilding.geometry.area.iloc[0] * floors
    else:
        print("Warning: No floor area found in tidybuilding")
        return pd.DataFrame(columns=['Prop_ID', 'zoning_id', 'allowed'])  # Return an empty DataFrame
    
    # Calculate FAR for each Prop_ID
    for prop_id, group in tidyparcel.groupby("Prop_ID"):
        parcel_without_centroid = group[(group['side'].notna()) & (group['side'] != "centroid")]
        polygons = list(polygonize(unary_union(parcel_without_centroid.geometry)))
        lot_polygon = unary_union(polygons)
        lot_area = lot_polygon.area * 10.7639

        if lot_area == 0:
            print(f"Warning: Lot area is zero for Prop_ID {prop_id}")
            continue

        far = fl_area / lot_area
    
        # Iterate through each row in tidyzoning
        for index, zoning_row in tidyzoning.iterrows():
            zoning_req = get_zoning_req(tidybuilding, zoning_row.to_frame().T)  # ✅ Fix the issue of passing Series

            # Fix the string check here
            if isinstance(zoning_req, str) and zoning_req == "No zoning requirements recorded for this district":
                results.append({'Prop_ID': prop_id, 'zoning_id': index, 'allowed': True})
                continue
            # If zoning_req is empty, consider it allowed
            if zoning_req is None or zoning_req.empty:
                results.append({'Prop_ID': prop_id, 'zoning_id': index, 'allowed': True})
                continue
            # Check if far meets the zoning constraints
            if 'far' in zoning_req['spec_type'].values:
                far_row = zoning_req[zoning_req['spec_type'] == 'far']  # Extract the specific row
                min_far = far_row['min_value'].values[0]  # Extract value
                max_far = far_row['max_value'].values[0]  # Extract value
                # Handle NaN values
                min_far = 0 if pd.isna(min_far) else min_far  # Set a very small value if no value
                max_far = 1000000 if pd.isna(max_far) else max_far  # Set a very large value if no value
                # Check the area range
                allowed = min_far <= far <= max_far
                results.append({'Prop_ID': prop_id, 'zoning_id': index, 'allowed': allowed})
            else:
                results.append({'Prop_ID': prop_id, 'zoning_id': index, 'allowed': True})  # If zoning has no constraints, default to True

    # Return a DataFrame containing the results for all zoning_ids
    return pd.DataFrame(results)