import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from tidyzoning import get_zoning_req

def check_unit_density(tidybuilding, tidyzoning, tidyparcel):
    """
    Checks whether the unit_density of a given building complies with zoning constraints.

    Parameters:
    ----------
    tidybuilding : A GeoDataFrame containing information about a single building. 
    tidyzoning : A GeoDataFrame containing zoning constraints. It may have multiple rows,
    tidyparcel : A GeoDataFrame containing parcel geometries, used to calculate the lot area.

    Returns:
    -------
    DataFrame
        A DataFrame with the following columns:
        - 'zoning_id': The index of the corresponding row from `tidyzoning`.
        - 'allowed': A boolean value indicating whether the building's building's unit density is compliant.
    """
    results = []
    # Check the data from the tidybuilding
    units_0bed = tidybuilding['units_0bed'].sum() if 'units_0bed' in tidybuilding.columns else 0
    units_1bed = tidybuilding['units_1bed'].sum() if 'units_1bed' in tidybuilding.columns else 0
    units_2bed = tidybuilding['units_2bed'].sum() if 'units_2bed' in tidybuilding.columns else 0
    units_3bed = tidybuilding['units_3bed'].sum() if 'units_3bed' in tidybuilding.columns else 0
    units_4bed = tidybuilding['units_4bed'].sum() if 'units_4bed' in tidybuilding.columns else 0
    total_units = units_0bed + units_1bed + units_2bed + units_3bed + units_4bed
    
    # Calculate FAR for each Parcel_ID
    for parcel_id, group in tidyparcel.groupby("parcel_id"):
        parcel_without_centroid = group[(group['side'].notna()) & (group['side'] != "centroid")]
        polygons = list(polygonize(unary_union(parcel_without_centroid.geometry)))
        lot_polygon = unary_union(polygons)
        lot_area = lot_polygon.area * 10.7639 / 43560 # Convert m2 to ft² , then to acres

        if lot_area == 0:
            print(f"Warning: Lot area is zero for parcel_id {parcel_id}")
            continue
        
        unit_density = total_units / lot_area #units per acre
        
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
            # Check if unit_density meets the zoning constraints
            if 'unit_density' in zoning_req['spec_type'].values:
                unit_density_row = zoning_req[zoning_req['spec_type'] == 'unit_density']  # Extract the specific row
                min_unit_density = unit_density_row['min_value'].values[0]  # Extract value
                max_unit_density = unit_density_row['max_value'].values[0]  # Extract value
                # Handle NaN values
                min_unit_density = 0 if pd.isna(min_unit_density) else min_unit_density  # Set a very small value if no value
                max_unit_density = 1000000 if pd.isna(max_unit_density) else max_unit_density  # Set a very large value if no value
                # Check the area range
                allowed = min_unit_density <= unit_density <= max_unit_density
                results.append({'parcel_id': parcel_id, 'zoning_id': index, 'allowed': allowed})
            else:
                results.append({'parcel_id': parcel_id, 'zoning_id': index, 'allowed': True})  # If zoning has no constraints, default to True

    # Return a DataFrame containing the results for all zoning_ids
    return pd.DataFrame(results)