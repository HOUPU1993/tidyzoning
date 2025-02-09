import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from tidyzoning import get_zoning_req

def check_unit_size(tidybuilding, tidyzoning):
    """
    Checks whether the floor area of a given building complies with zoning constraints.

    Parameters:
    ----------
    tidybuilding : GeoDataFrame
        A GeoDataFrame containing information about a single building. 
        It must have at least one of the following:
        - 'floor_area' column: Directly specifying the building's floor area.
        - 'total_floors' column and 'geometry': If 'floor_area' is missing, 
          the total floor area is estimated by multiplying the footprint area 
          (from 'geometry') by the number of floors.

    tidyzoning : GeoDataFrame
        A GeoDataFrame containing zoning constraints. It may have multiple rows,
        each representing a different zoning rule that applies to the given building.
    
    Returns:
    -------
    DataFrame
        A DataFrame with two columns:
        - 'zoning_id': The index of the corresponding row from `tidyzoning`.
        - 'allowed': A boolean value indicating whether the building's floor area 
          complies with the zoning regulations (True if compliant, False otherwise).
    """
    ureg = UnitRegistry()
    results = []

    # Determine min_size and max_size based on tidybuilding DataFrame
    if len(tidybuilding['max_unit_size']) == 1 and len(tidybuilding['min_unit_size']) == 1:
        min_size = tidybuilding['min_unit_size'].iloc[0] * ureg('ft^2')
        max_size = tidybuilding['max_unit_size'].iloc[0] * ureg('ft^2')
    elif len(tidybuilding['max_unit_size']) == 1:
        min_size = tidybuilding['max_unit_size'].iloc[0] * ureg('ft^2')
        max_size = tidybuilding['max_unit_size'].iloc[0] * ureg('ft^2')
    elif len(tidybuilding['min_unit_size']) == 1:
        min_size = tidybuilding['min_unit_size'].iloc[0] * ureg('ft^2')
        max_size = tidybuilding['min_unit_size'].iloc[0] * ureg('ft^2')
    else:
        print("Warning: No valid unit sizes found in tidybuilding")
        return pd.DataFrame(columns=['zoning_id', 'allowed'])  # Return an empty DataFrame

    # Iterate through each row in tidyzoning
    for index, zoning_row in tidyzoning.iterrows():
        zoning_req = get_zoning_req(tidybuilding, zoning_row.to_frame().T)  # ✅ Fix the issue of passing Series

        # If zoning_req is empty, consider it allowed
        if zoning_req is None or zoning_req.empty:
            results.append({'zoning_id': index, 'allowed': True})
            continue

        # Check if unit_size meets the zoning constraints
        if 'unit_size' in zoning_req['spec_type'].values:
            unit_size_row = zoning_req[zoning_req['spec_type'] == 'unit_size']  # Extract the specific row
            min_unit_size = unit_size_row['min_value'].values[0]  # Extract value
            max_unit_size = unit_size_row['max_value'].values[0]  # Extract value

            # Handle NaN values
            min_unit_size = 0 if pd.isna(min_unit_size) else min_unit_size  # Set a very small value if no value
            max_unit_size = 1000000 if pd.isna(max_unit_size) else max_unit_size  # Set a very large value if no value

            # Get the unit and convert
            unit_column = unit_size_row['unit'].values[0]  # Extract the unit of the specific row
            # Define the unit mapping
            unit_mapping = {
                "square feet": ureg('ft^2'),
                "square meters": ureg('m^2'),
                "acres": ureg('acre')
            }
            target_unit = unit_mapping.get(unit_column, ureg('ft^2'))  # Convert the unit of the specific row to a unit recognized by pint, default is ft^2 if no unit
            # Ensure min/max_unit_size has the correct unit 'ft^2'
            min_unit_size = ureg.Quantity(min_unit_size, target_unit).to('ft^2')
            max_unit_size = ureg.Quantity(max_unit_size, target_unit).to('ft^2')

            # Check the area range
            allowed = min_size >= min_unit_size and max_size <= max_unit_size
            results.append({'zoning_id': index, 'allowed': allowed})
        else:
            results.append({'zoning_id': index, 'allowed': True})  # If zoning has no constraints, default to True

    # Return a DataFrame containing the results for all zoning_ids
    return pd.DataFrame(results)