import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from tidyzoning import get_zoning_req

def check_fl_area(tidybuilding, tidyzoning):
    """
    Checks whether the floor area of a given building complies with zoning constraints.

    Parameters:
    ----------
    tidybuilding : GeoDataFrame
        A GeoDataFrame containing information about a single building. 
        It must have at least one of the following:
        - 'fl_area' column: Directly specifying the building's floor area.
        - 'total_floors' column and 'geometry': If 'fl_area' is missing, 
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

    # Calculate the floor area of the building
    if len(tidybuilding['fl_area']) == 1:
        fl_area = tidybuilding['fl_area'].iloc[0] * ureg('ft^2')
    elif len(tidybuilding['total_floors']) == 1:
        floors = tidybuilding['total_floors'].iloc[0]
        fl_area = tidybuilding.geometry.area.iloc[0] * floors * ureg('ft^2')
    else:
        print("Warning: No floor area found in tidybuilding")
        return pd.DataFrame(columns=['zoning_id', 'allowed'])  # Return an empty DataFrame

    # Iterate through each row in tidyzoning
    for index, zoning_row in tidyzoning.iterrows():
        zoning_req = get_zoning_req(tidybuilding, zoning_row.to_frame().T)  # ✅ Fix the issue of passing Series

        # If zoning_req is empty, consider it allowed
        if zoning_req is None or zoning_req.empty:
            results.append({'zoning_id': index, 'allowed': True})
            continue

        # Check if fl_area meets the zoning constraints
        if 'fl_area' in zoning_req['spec_type'].values:
            fl_area_row = zoning_req[zoning_req['spec_type'] == 'fl_area']  # Extract the specific row
            min_fl_area = fl_area_row['min_value'].values[0]  # Extract value
            max_fl_area = fl_area_row['max_value'].values[0]  # Extract value

            # Handle NaN values
            min_fl_area = 0 if pd.isna(min_fl_area) else min_fl_area  # Set a very small value if no value
            max_fl_area = 1000000 if pd.isna(max_fl_area) else max_fl_area  # Set a very large value if no value

            # Get the unit and convert
            unit_column = fl_area_row['unit'].values[0]  # Extract the unit of the specific row
            # Define the unit mapping
            unit_mapping = {
                "square feet": ureg('ft^2'),
                "square meters": ureg('m^2'),
                "acres": ureg('acre')
            }
            target_unit = unit_mapping.get(unit_column, ureg('ft^2'))  # Convert the unit of the specific row to a unit recognized by pint, default is ft^2 if no unit
            # Ensure min/max_fl_area has the correct unit 'ft^2'
            min_fl_area = ureg.Quantity(min_fl_area, target_unit).to('ft^2')
            max_fl_area = ureg.Quantity(max_fl_area, target_unit).to('ft^2')

            # Check the area range
            allowed = min_fl_area <= fl_area <= max_fl_area
            results.append({'zoning_id': index, 'allowed': allowed})
        else:
            results.append({'zoning_id': index, 'allowed': True})  # If zoning has no constraints, default to True

    # Return a DataFrame containing the results for all zoning_ids
    return pd.DataFrame(results)