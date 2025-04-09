import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from tidyzoning import get_zoning_req

def check_height_eave(tidybuilding, tidyzoning, tidyparcel=None):
    """
    Checks whether the building height_eave of a given building complies with zoning constraints.

    Parameters:
    ----------
    tidybuilding : A GeoDataFrame containing information about a single building. 
    tidyzoning : A GeoDataFrame containing zoning constraints. It may have multiple rows,
    tidyparcel : Optional
    
    Returns:
    -------
    DataFrame
        A DataFrame with the following columns:
        - 'zoning_id': The index of the corresponding row from `tidyzoning`.
        - 'allowed': A boolean value indicating whether the building's Height
        - 'constraint_min_note': The constraint note for the minimum value.
        - 'constraint_max_note': The constraint note for the maximum value.
        
    How to use:
    check_height_eave_result = check_height_eave(tidybuilding_4_fam, tidyzoning, tidyparcel[tidyparcel['parcel_id'] == '10'])
    """
    ureg = UnitRegistry()
    results = []

    # Calculate the floor area of the building
    if len(tidybuilding['height_eave']) == 1:
        height_eave = tidybuilding['height_eave'].iloc[0]
    else:
        return pd.DataFrame(columns=['zoning_id', 'allowed', 'constraint_min_note', 'constraint_max_note']) # Return an empty DataFrame
    
    # Iterate through each row in tidyzoning
    for index, zoning_row in tidyzoning.iterrows():
        zoning_req = get_zoning_req(tidybuilding, zoning_row.to_frame().T, tidyparcel)  # ✅ Fix the issue of passing Series

        # Fix the string check here
        if isinstance(zoning_req, str) and zoning_req == "No zoning requirements recorded for this district":
            results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': None, 'constraint_max_note': None})
            continue
        # If zoning_req is empty, consider it allowed
        if zoning_req is None or zoning_req.empty:
            results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': None, 'constraint_max_note': None})
            continue
        # Check if zoning constraints include 'height_eave'
        if 'height_eave' in zoning_req['spec_type'].values:
            height_eave_row = zoning_req[zoning_req['spec_type'] == 'height_eave']
            min_height_eave = height_eave_row['min_value'].values[0]  # Extract min values
            max_height_eave = height_eave_row['max_value'].values[0]  # Extract max values
            min_select = height_eave_row['min_select'].values[0]  # Extract min select info
            max_select = height_eave_row['max_select'].values[0]  # Extract max select info
            constraint_min_note = height_eave_row['constraint_min_note'].values[0] # Extract min constraint note
            constraint_max_note = height_eave_row['constraint_max_note'].values[0] # Extract max constraint note
            
            # If min_select or max_select is 'OZFS Error', default to allowed
            if min_select == 'OZFS Error' or max_select == 'OZFS Error':
                results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})
                continue

            # Handle NaN values and list
            # Handle min_height_eave
            if not isinstance(min_height_eave, list):
                min_height_eave = [0] if min_height_eave is None or pd.isna(min_height_eave) or isinstance(min_height_eave, str) else [min_height_eave]
            else:
                # Filter out NaN and None values, ensuring at least one valid value
                min_height_eave = [v for v in min_height_eave if pd.notna(v) and v is not None and not isinstance(v, str)]
                if not min_height_eave:  # If all values are NaN or None, replace with default value
                    min_height_eave = [0]
            # Handle max_height_eave
            if not isinstance(max_height_eave, list):
                max_height_eave = [1000000] if max_height_eave is None or pd.isna(max_height_eave) or isinstance(max_height_eave, str) else [max_height_eave]
            else:
                # Filter out NaN and None values, ensuring at least one valid value
                max_height_eave = [v for v in max_height_eave if pd.notna(v) and v is not None and not isinstance(v, str)]
                if not max_height_eave:  # If all values are NaN or None, replace with default value
                    max_height_eave = [1000000]

            # Get the unit and convert
            unit_column = height_eave_row['unit'].values[0]  # Extract the unit of the specific row
            # Define the unit mapping
            unit_mapping = {
                "feet": ureg('ft'),
                "meters": ureg('m'),
            }
            target_unit = unit_mapping.get(unit_column, ureg('ft'))  # Convert the unit of the specific row to a unit recognized by pint, default is ft^2 if no unit
            # Ensure min/max_height_eave has the correct unit 'ft^2'
            min_height_eave = [ureg.Quantity(v, target_unit).to('ft').magnitude for v in min_height_eave]
            max_height_eave = [ureg.Quantity(v, target_unit).to('ft').magnitude for v in max_height_eave]

            # Check min condition
            min_check_1 = min(min_height_eave) <= height_eave
            min_check_2 = max(min_height_eave) <= height_eave
            if min_select in ["either", None]:
                min_allowed = min_check_1 or min_check_2
            elif min_select == "unique":
                if min_check_1 and min_check_2:
                    min_allowed = True
                elif not min_check_1 and not min_check_2:
                    min_allowed = False
                else:
                    min_allowed = "MAYBE"
            
            # Check max condition
            max_check_1 = min(max_height_eave) >= height_eave
            max_check_2 = max(max_height_eave) >= height_eave
            if max_select in ["either", None]:
                max_allowed = max_check_1 or max_check_2
            elif max_select == "unique":
                if max_check_1 and max_check_2:
                    max_allowed = True
                elif not max_check_1 and not max_check_2:
                    max_allowed = False
                else:
                    max_allowed = "MAYBE"
            
            # Determine final allowed status
            if min_allowed == "MAYBE" or max_allowed == "MAYBE":
                allowed = "MAYBE"
            else:
                allowed = min_allowed and max_allowed
            
            results.append({'zoning_id': index, 'allowed': allowed, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})
        else:
            results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': None, 'constraint_max_note': None})  # If zoning has no constraints, default to True

    return pd.DataFrame(results)