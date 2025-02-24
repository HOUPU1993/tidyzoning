import pandas as pd

def find_bldg_type(tidybuilding):
    """
    Determines the building type directly from the 'type' column in the tidybuilding DataFrame.

    Parameters:
        tidybuilding (pd.DataFrame): A DataFrame containing a 'type' column.

    Returns:
        str: The building type as stored in the 'type' column.
    """
    if "type" in tidybuilding.columns:
        return tidybuilding["type"].iloc[0]  # Assuming only one building per DataFrame
    else:
        return "other"
