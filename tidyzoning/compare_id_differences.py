import pandas as pd

def compare_id_differences(df_houpu, df_kamryn, kamryn_filter_col='check_far'):
    """
    Compare the differences in 'zoning_id' and 'parcel_id' between two datasets that meet specific conditions,
    and directly print the results.

    Parameters:
      df_houpu: The first dataset, which contains the fields 'allowed', 'zoning_id', and 'parcel_id'.
      df_kamryn: The second dataset, which contains the filtering field (default is 'check_far'), 
                 'zoning_id', and 'parcel_id'.
      kamryn_filter_col: The name of the field used for filtering df_kamryn. Default value is 'check_far'.

    Processing logic:
      - Filter df_houpu: retain records where 'allowed' is False or 'MAYBE'.
      - Filter df_kamryn: retain records where the filtering field (kamryn_filter_col) is False or 'MAYBE'.
      - Compare the filtered 'zoning_id' and 'parcel_id' values by computing the differences.
      - Print the results as follows:
            "Only in the first dataset for <field>: set(...)"
            "Only in kamryn_results for <field>: set(...)"

    Example:
      compare_id_differences(check_far_result_all, kamryn_results, kamryn_filter_col='check_far')
    """
    # Define the fields to compare: only 'zoning_id' and 'parcel_id'
    compare_cols = ['zoning_id', 'parcel_id']
    
    # Filter df_houpu: retain records where 'allowed' is False or 'MAYBE'
    filtered_all = df_houpu[(df_houpu['allowed'] == False) | (df_houpu['allowed'] == 'MAYBE')]
    # Filter df_kamryn: retain records where the filtering field is False or 'MAYBE'
    filtered_kamryn = df_kamryn[(df_kamryn[kamryn_filter_col] == False) | (df_kamryn[kamryn_filter_col] == 'MAYBE')]
    
    # Loop over the fields to compare, calculate and print the differences
    for col in compare_cols:
        set_all = set(filtered_all[col])
        set_kamryn = set(filtered_kamryn[col])
        
        only_in_all = set_all - set_kamryn
        only_in_kamryn = set_kamryn - set_all
        
        print("Only in the first dataset for {}: {}".format(col, only_in_all))
        print("Only in kamryn_results for {}: {}".format(col, only_in_kamryn))