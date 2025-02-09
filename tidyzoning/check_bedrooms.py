import pandas as pd
import numpy as np
import geopandas as gpd
from tidyzoning import get_zoning_req

def check_bedrooms(tidybuilding, tidyzoning):
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
        - 'zoning_id': The index of the corresponding row from `tidyzoning`.
        - 'allowed': A boolean value indicating whether the building's FAR 
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
        print("Warning: No bedrooms found in tidybuilding")
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
        # Check if bedrooms meets the zoning constraints
        if 'bedrooms' in zoning_req['spec_type'].values:
            bedrooms_row = zoning_req[zoning_req['spec_type'] == 'bedrooms']  # Extract the specific row
            min_bedrooms = bedrooms_row['min_value'].values[0]  # Extract value
            max_bedrooms = bedrooms_row['max_value'].values[0]  # Extract value
            # Handle NaN values
            min_bedrooms = 0 if pd.isna(min_bedrooms) else min_bedrooms  # Set a very small value if no value
            max_bedrooms = 1000000 if pd.isna(max_bedrooms) else max_bedrooms  # Set a very large value if no value
            # Check the area range
            allowed = min_beds >= min_bedrooms and  max_beds <= max_bedrooms
            results.append({'zoning_id': index, 'allowed': allowed})
        else:
            results.append({'zoning_id': index, 'allowed': True})  # If zoning has no constraints, default to True

    # Return a DataFrame containing the results for all zoning_ids
    return pd.DataFrame(results)