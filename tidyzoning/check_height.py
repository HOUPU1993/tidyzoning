import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from tidyzoning import get_zoning_req

def check_height(tidybuilding, tidyzoning):
    """
    Checks whether the Floor Area Ratio (FAR) of a given building complies with zoning constraints.

    Parameters:
    ----------
    tidybuilding : A GeoDataFrame containing information about a single building. 
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
    if len(tidybuilding['building_height']) == 1:
        height = tidybuilding['building_height'].iloc[0] * ureg('ft')
    elif len(tidybuilding['total_floors']) == 1:
        floors = tidybuilding['total_floors'].iloc[0]
        height = 12 * floors * ureg('ft') # height was recorded as feet
    else:
        print("Warning: No tidybuilding height recorded")
        return pd.DataFrame(columns=['zoning_id', 'allowed'])  # Return an empty DataFrame
    
    # Iterate through each row in tidyzoning
    for index, zoning_row in tidyzoning.iterrows():
        zoning_req = get_zoning_req(tidybuilding, zoning_row.to_frame().T)  # ✅ Fix the issue of passing Series

        # Fix the string check here
        if isinstance(zoning_req, str) and zoning_req == "No zoning requirements recorded for this district":
            results.append({'zoning_id': index, 'allowed': True})
            continue
        # If zoning_req is empty, consider it allowed
        if zoning_req is None or zoning_req.empty:
            results.append({'zoning_id': index, 'allowed': True})
            continue
        # Check if far meets the zoning constraints
        if 'height' in zoning_req['spec_type'].values:
            height_row = zoning_req[zoning_req['spec_type'] == 'height']  # Extract the specific row
            min_height = height_row['min_value'].values[0]  # Extract value
            max_height = height_row['max_value'].values[0]  # Extract value
            # Handle NaN values
            # min_height = 0 if pd.isna(min_height) else min_height  # Set a very small value if no value
            # max_height = 1000000 if pd.isna(max_height) else max_height  # Set a very large value if no value

            if isinstance(min_height, list):
                min_height = np.array(min_height, dtype=float)  
                min_height = 0 if np.isnan(min_height).all() else np.nanmin(min_height)  
            else:
                min_height = 0 if pd.isna(min_height) else min_height  

            if isinstance(max_height, list):
                max_height = np.array(max_height, dtype=float) 
                max_height = 1000000 if np.isnan(max_height).all() else np.nanmin(max_height)  
            else:
                max_height = 1000000 if pd.isna(max_height) else max_height 

            # Get the unit and convert
            unit_column = height_row['unit'].values[0]  # Extract the unit of the specific row
            # Define the unit mapping
            unit_mapping = {
                "feet": ureg('ft'),
                "meters": ureg('m'),
            }
            target_unit = unit_mapping.get(unit_column, ureg('ft'))  # Convert the unit of the specific row to a unit recognized by pint, default is ft if no unit
            # Ensure min/max_height has the correct unit 'ft'
            min_height = ureg.Quantity(min_height, target_unit).to('ft')
            max_height = ureg.Quantity(max_height, target_unit).to('ft')
            
            # Check the area range
            allowed = min_height <= height <= max_height
            results.append({'zoning_id': index, 'allowed': allowed})
        else:
            results.append({'zoning_id': index, 'allowed': True})  # If zoning has no constraints, default to True

    # Return a DataFrame containing the results for all zoning_ids
    return pd.DataFrame(results)