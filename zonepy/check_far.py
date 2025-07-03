import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from zonepy import get_zoning_req

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
        - 'parcel_id': Identifier for the property (from `tidyparcel`).
        - 'zoning_id': The index of the corresponding row from `tidyzoning`.
        - 'allowed': A boolean value indicating whether the building's FAR 
        - 'constraint_min_note': The constraint note for the minimum value.
        - 'constraint_max_note': The constraint note for the maximum value.
        
    How to use:
    check_far_results = check_far(tidybuilding_4_fam, tidyzoning, tidyparcel[tidyparcel['parcel_id'] == '10'])
    """
    ureg = UnitRegistry()
    results = []

    # Calculate the floor area of the building
    if len(tidybuilding['gross_fl_area']) == 1:
        fl_area = tidybuilding['gross_fl_area'].iloc[0]
    else:
        return pd.DataFrame(columns=['zoning_id', 'allowed', 'constraint_min_note', 'constraint_max_note']) # Return an empty DataFrame

    # Calculate FAR for each Parcel_ID
    lot_area = tidyparcel["lot_area"].iloc[0] if tidyparcel is not None and not tidyparcel.empty else None
    if lot_area is not None and lot_area != 0:
        far = fl_area / (lot_area * 43560) # Convert lot area from acres to square feet
    else:
        far = 0  # or maybe 0 or np.nan depending on your context

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
        # Check if zoning constraints include 'far'
        if 'far' in zoning_req['spec_type'].values:
            far_row = zoning_req[zoning_req['spec_type'] == 'far']
            min_far = far_row['min_value'].values[0]  # Extract min values
            max_far = far_row['max_value'].values[0]  # Extract max values
            min_select = far_row['min_select'].values[0]  # Extract min select info
            max_select = far_row['max_select'].values[0]  # Extract max select info
            constraint_min_note = far_row['constraint_min_note'].values[0] # Extract min constraint note
            constraint_max_note = far_row['constraint_max_note'].values[0] # Extract max constraint note
            
            # If min_select or max_select is 'OZFS Error', default to allowed
            if min_select == 'OZFS Error' or max_select == 'OZFS Error':
                results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})
                continue
            
            # Handle NaN values and list
            # Handle min_far
            if not isinstance(min_far, list):
                min_far = [0] if min_far is None or pd.isna(min_far) or isinstance(min_far, str) else [min_far]
            else:
                # Filter out NaN and None values, ensuring at least one valid value
                min_far = [v for v in min_far if pd.notna(v) and v is not None and not isinstance(v, str)]
                if not min_far:  # If all values are NaN or None, replace with default value
                    min_far = [0]
            # Handle max_far
            if not isinstance(max_far, list):
                max_far = [1000000] if max_far is None or pd.isna(max_far) or isinstance(max_far, str) else [max_far]
            else:
                # Filter out NaN and None values, ensuring at least one valid value
                max_far = [v for v in max_far if pd.notna(v) and v is not None and not isinstance(v, str)]
                if not max_far:  # If all values are NaN or None, replace with default value
                    max_far = [1000000]
            
            # Check min condition
            min_check_1 = min(min_far) <= far
            min_check_2 = max(min_far) <= far
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
            max_check_1 = min(max_far) >= far
            max_check_2 = max(max_far) >= far
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

    # Return a DataFrame containing the results for all zoning_ids
    return pd.DataFrame(results)