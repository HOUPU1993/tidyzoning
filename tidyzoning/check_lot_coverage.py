import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from tidyzoning import get_zoning_req

def check_lot_coverage(tidybuilding, tidyzoning, tidyparcel):
    """
    Checks whether the lot_coverage of a given building complies with zoning constraints.

    Parameters:
    ----------
    tidybuilding : A GeoDataFrame containing information about a single building. 
    tidyparcel : A GeoDataFrame containing information about the tidyparcels(single/multiple ). 
    tidyzoning : A GeoDataFrame containing zoning constraints. It may have multiple rows,

    Returns:
    -------
    DataFrame
        A DataFrame with the following columns:
        - 'parcel_id': Identifier for the property (from `tidyparcel`).
        - 'zoning_id': The index of the corresponding row from `tidyzoning`.
        - 'allowed': A boolean value indicating whether the building's lot coverage 
    """
    ureg = UnitRegistry()
    results = []

    # Calculate the floor area of the building
    if len(tidybuilding['fl_area_bottom']) == 1:
        footprint = tidybuilding['fl_area_bottom'].iloc[0] * ureg('ft^2')
    elif len(tidybuilding['stories']) == 1 and len(tidybuilding['fl_area']) == 1:
        floors = tidybuilding['stories'].iloc[0]
        fl_area = tidybuilding['fl_area'].iloc[0]
        footprint = (fl_area / floors) * ureg('ft^2')
    elif len(tidybuilding['geometry']) == 1:
        footprint = tidybuilding.geometry.area.iloc[0] * ureg('m^2')
        footprint = footprint.to('ft^2')
    else:
        print("Warning: No floor area found in tidybuilding")
        return pd.DataFrame(columns=['parcel_id', 'zoning_id', 'allowed'])  # Return an empty DataFrame
    
    # Calculate lot_coverage for each parcel_id
    for parcel_id, group in tidyparcel.groupby("parcel_id"):
        parcel_without_centroid = group[(group['side'].notna()) & (group['side'] != "centroid")]
        polygons = list(polygonize(unary_union(parcel_without_centroid.geometry)))
        lot_polygon = unary_union(polygons)
        lot_area = lot_polygon.area * 10.7639

        if lot_area == 0:
            print(f"Warning: Lot area is zero for parcel_id {parcel_id}")
            continue

        lot_coverage = (footprint / lot_area) * 100
        lot_coverage = lot_coverage.magnitude # transfer into value, delete unit
        
        # Iterate through each row in tidyzoning
        for index, zoning_row in tidyzoning.iterrows():
            zoning_req = get_zoning_req(tidybuilding, zoning_row.to_frame().T)  # ✅ Fix the issue of passing Series

            # Fix the string check here
            if isinstance(zoning_req, str) and zoning_req == "No zoning requirements recorded for this district":
                results.append({'parcel_id': parcel_id, 'zoning_id': index, 'allowed': True})
                continue
            # If zoning_req is empty, consider it allowed
            if zoning_req is None or zoning_req.empty:
                results.append({'parcel_id': parcel_id, 'zoning_id': index, 'allowed': True})
                continue
            # Check if lot_coverage meets the zoning constraints
            if 'lot_coverage' in zoning_req['spec_type'].values:
                lot_coverage_row = zoning_req[zoning_req['spec_type'] == 'lot_coverage']  # Extract the specific row
                min_lot_coverage = lot_coverage_row['min_value'].values[0]  # Extract value
                max_lot_coverage = lot_coverage_row['max_value'].values[0]  # Extract value
                # Handle NaN values
                min_lot_coverage = 0 if pd.isna(min_lot_coverage) else min_lot_coverage  # Set a very small value if no value
                max_lot_coverage = 100 if pd.isna(max_lot_coverage) else max_lot_coverage  # Set a very large value if no value
                # Check the area range
                allowed = min_lot_coverage <= lot_coverage <= max_lot_coverage
                results.append({'parcel_id': parcel_id, 'zoning_id': index, 'allowed': allowed})
            else:
                results.append({'parcel_id': parcel_id, 'zoning_id': index, 'allowed': True})  # If zoning has no constraints, default to True

    # Return a DataFrame containing the results for all zoning_ids
    return pd.DataFrame(results)