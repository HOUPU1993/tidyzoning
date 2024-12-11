import pandas as pd

def find_bldg_type(tidybuilding):
    # define the interested columns
    possible_columns = ["units_0bed", "units_1bed", "units_2bed", "units_3bed", "units_4bed"]
    
    # Filter the columns of interest, removing irrelevant columns
    available_columns = [col for col in possible_columns if col in tidybuilding.columns]
    tidybuilding = tidybuilding[available_columns]
    
    # calculate the sum of row
    row_sum = tidybuilding.sum(axis=1).iloc[0]
    
    # return the result
    if row_sum in [1, 2, 3]:
        return f"{int(row_sum)}_family"
    elif row_sum > 3:
        return "4_family"
    else:
        return "other"