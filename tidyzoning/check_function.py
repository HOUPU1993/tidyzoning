import pandas as pd

def check_land_use(tidybuilding, tidyzoning):
    """
    Checks if the tidybuilding is allowed in each row of tidyzoning DataFrame based on land use.

    Parameters:
        tidybuilding (object): The input data for which the building type will be computed.
        tidyzoning (pd.DataFrame): The zoning DataFrame with a 'dist_info' column containing zoning info dictionary.

    Returns:
        pd.DataFrame: A DataFrame with the 'allowed' column indicating if the building is allowed and corresponding tidyzoning idex.
    """
    def check_land_use_single(dist_info, bldg_type):
        # Extract uses_permitted from dist_info dictionary
        uses_permitted = dist_info.get("uses_permitted", {})
        uses_value = uses_permitted.get("uses_value", [])

        # Handle edge cases
        if bldg_type == "other":
            return False
        if not uses_value:
            return False

        # Check if the building type is in the list of permitted uses
        return bldg_type in uses_value

    # Compute the building type
    bldg_type = find_bldg_type(tidybuilding)
    # Apply the check function to the dist_info column
    tidyzoning["allowed"] = tidyzoning["dist_info"].apply(lambda x: check_land_use_single(x, bldg_type))
    
    # Create a new DataFrame with 'zoning_id' and 'allowed' columns
    results_df = tidyzoning[["allowed"]].reset_index()
    results_df.rename(columns={"index": "zoning_id"}, inplace=True)
    
    return results_df