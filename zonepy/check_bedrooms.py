import pandas as pd
import numpy as np
import geopandas as gpd
from zonepy import get_zoning_req

def check_bedrooms(tidybuilding, tidyzoning, tidyparcel=None):
    """
    Checks whether the bedrooms of a given building complies with zoning constraints.

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
        - 'allowed': A boolean value indicating whether the building's bedrooms 
        - 'constraint_min_note': The constraint note for the minimum value.
        - 'constraint_max_note': The constraint note for the maximum value.
        
    How to use:
    check_bedrooms_result = check_bedrooms(tidybuilding_4_fam, tidyzoning, tidyparcel[tidyparcel['parcel_id'] == '10'])
    """
    results = []
    # Check the data from the tidybuilding
    bed_list = {
        'units_0bed': 0,
        'units_1bed': 1,
        'units_2bed': 2,
        'units_3bed': 3,
        'units_4bed': 4
    }
    # find units_Xbed column in tidybuilding
    matching_beds = [bed_list[col] for col in tidybuilding.columns if col in bed_list]
    # find min_beds and max_beds
    if matching_beds:
        min_beds = min(matching_beds)
        max_beds = max(matching_beds)
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
        # Check if zoning constraints include 'bedrooms'
        if 'bedrooms' in zoning_req['spec_type'].values:
            bedrooms_row = zoning_req[zoning_req['spec_type'] == 'bedrooms']
            min_bedrooms = bedrooms_row['min_value'].values[0]  # Extract min values
            max_bedrooms = bedrooms_row['max_value'].values[0]  # Extract max values
            min_select = bedrooms_row['min_select'].values[0]  # Extract min select info
            max_select = bedrooms_row['max_select'].values[0]  # Extract max select info
            constraint_min_note = bedrooms_row['constraint_min_note'].values[0] # Extract min constraint note
            constraint_max_note = bedrooms_row['constraint_max_note'].values[0] # Extract max constraint note
            
            # If min_select or max_select is 'OZFS Error', default to allowed
            if min_select == 'OZFS Error' or max_select == 'OZFS Error':
                results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})
                continue

            # Handle NaN values and list
            # Handle min_bedrooms
            if not isinstance(min_bedrooms, list):
                min_bedrooms = [0] if min_bedrooms is None or pd.isna(min_bedrooms) or isinstance(min_bedrooms, str) else [min_bedrooms]
            else:
                # Filter out NaN and None values, ensuring at least one valid value
                min_bedrooms = [v for v in min_bedrooms if pd.notna(v) and v is not None and not isinstance(v, str)]
                if not min_bedrooms:  # If all values are NaN or None, replace with default value
                    min_bedrooms = [0]
            # Handle max_bedrooms
            if not isinstance(max_bedrooms, list):
                max_bedrooms = [100] if max_bedrooms is None or pd.isna(max_bedrooms) or isinstance(max_bedrooms, str) else [max_bedrooms]
            else:
                # Filter out NaN and None values, ensuring at least one valid value
                max_bedrooms = [v for v in max_bedrooms if pd.notna(v) and v is not None and not isinstance(v, str)]
                if not max_bedrooms:  # If all values are NaN or None, replace with default value
                    max_bedrooms = [100]
            
            # Check min condition
            min_check_1 = min(min_bedrooms) <= min_beds
            min_check_2 = max(min_bedrooms) <= min_beds
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
            max_check_1 = min(max_bedrooms) >= max_beds
            max_check_2 = max(max_bedrooms) >= max_beds
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