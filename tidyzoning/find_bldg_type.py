import pandas as pd

# def find_bldg_type(tidybuilding):
#     """
#     Determines the building type based on the number of units in the tidybuilding DataFrame.

#     Parameters:
#         tidybuilding (pd.DataFrame): A DataFrame containing unit information for a building.
#                                      Columns include'units_0bed', 'units_1bed', 'units_2bed', 'units_3bed', and 'units_4bed'.
#                                      Each column represents the number of units of a specific type.

#     Returns:
#         str: A string representing the building type:
#              - "1_family", "2_family", or "3_family" for buildings with 1, 2, or 3 units.
#              - "4_family" for buildings with more than 3 units.
#              - "other" for buildings with no units or invalid data.
#     """
#     # define the interested columns
#     possible_columns = ["units_0bed", "units_1bed", "units_2bed", "units_3bed", "units_4bed"]
    
#     # Filter the columns of interest, removing irrelevant columns
#     available_columns = [col for col in possible_columns if col in tidybuilding.columns]
#     tidybuilding = tidybuilding[available_columns]
    
#     # calculate the sum of row
#     row_sum = tidybuilding.sum(axis=1).iloc[0]
    
#     # return the result
#     if row_sum in [1, 2, 3]:
#         return f"{int(row_sum)}_family"
#     elif row_sum > 3:
#         return "4_family"
#     else:
#         return "other"
    
    
    
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
