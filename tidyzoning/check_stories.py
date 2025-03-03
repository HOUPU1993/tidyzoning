import pandas as pd
import numpy as np
import geopandas as gpd
from tidyzoning import get_zoning_req

def check_stories(tidybuilding, tidyzoning):
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
    """
    results = []

    # Calculate the floor area of the building
    if len(tidybuilding['stories']) == 1:
        stories = tidybuilding['stories'].iloc[0]
    else:
        print("Warning: No tidybuilding stories recorded")
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
        # Check if stories meets the zoning constraints
        if 'stories' in zoning_req['spec_type'].values:
            stories_row = zoning_req[zoning_req['spec_type'] == 'stories']  # Extract the specific row
            min_stories = stories_row['min_value'].values[0]  # Extract value
            max_stories = stories_row['max_value'].values[0]  # Extract value
            # Handle NaN values
            min_stories = 0 if pd.isna(min_stories) else min_stories  # Set a very small value if no value
            max_stories = 1000000 if pd.isna(max_stories) else max_stories  # Set a very large value if no value
            # Check the area range
            allowed = min_stories <= stories <= max_stories
            results.append({'zoning_id': index, 'allowed': allowed})
        else:
            results.append({'zoning_id': index, 'allowed': True})  # If zoning has no constraints, default to True

    # Return a DataFrame containing the results for all zoning_ids
    return pd.DataFrame(results)