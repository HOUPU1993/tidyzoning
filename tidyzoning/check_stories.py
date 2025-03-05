import pandas as pd
import numpy as np
import geopandas as gpd
from tidyzoning import get_zoning_req

def check_stories(tidybuilding, tidyzoning, tidyparcel=None):
    """
    Checks whether the bedrooms of a given building complies with zoning constraints.

    Parameters:
    ----------
    tidybuilding : A GeoDataFrame containing information about a single building. 
    tidyzoning : A GeoDataFrame containing zoning constraints. It may have multiple rows,

    Returns:
    -------
    DataFrame
        A DataFrame with the following columns:
        - 'zoning_id': The index of the corresponding row from `tidyzoning`.
        - 'allowed': A boolean value indicating whether the building's stories 
        - 'constraint_min_note': The constraint note for the minimum value.
        - 'constraint_max_note': The constraint note for the maximum value.
    """
    results = []

    # Calculate the floor area of the building
    if len(tidybuilding['stories']) == 1:
        stories = tidybuilding['stories'].iloc[0]
    else:
        print("Warning: No tidybuilding stories recorded")
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
        # Check if zoning constraints include 'stories'
        if 'stories' in zoning_req['spec_type'].values:
            stories_row = zoning_req[zoning_req['spec_type'] == 'stories']
            min_stories = stories_row['min_value'].values[0]  # Extract min values
            max_stories = stories_row['max_value'].values[0]  # Extract max values
            min_select = stories_row['min_select'].values[0]  # Extract min select info
            max_select = stories_row['max_select'].values[0]  # Extract max select info
            constraint_min_note = stories_row['constraint_min_note'].values[0] # Extract min constraint note
            constraint_max_note = stories_row['constraint_max_note'].values[0] # Extract max constraint note
            
            # If min_select or max_select is 'OZFS Error', default to allowed
            if min_select == 'OZFS Error' or max_select == 'OZFS Error':
                results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})
                continue
            
            # Handle NaN values and list
            # Handle min_stories
            if not isinstance(min_stories, list):
                min_stories = [0] if min_stories is None or pd.isna(min_stories) else [min_stories]
            elif all(pd.isna(v) for v in min_stories):  # Handle list of NaNs
                min_stories = [0]

            # Handle max_stories
            if not isinstance(max_stories, list):
                max_stories = [1000000] if max_stories is None or pd.isna(max_stories) else [max_stories]
            elif all(pd.isna(v) for v in max_stories):  # Handle list of NaNs
                max_stories = [1000000]
            
            # Check min condition
            min_check_1 = min(min_stories) <= stories
            min_check_2 = max(min_stories) <= stories
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
            max_check_1 = min(max_stories) >= stories
            max_check_2 = max(max_stories) >= stories
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