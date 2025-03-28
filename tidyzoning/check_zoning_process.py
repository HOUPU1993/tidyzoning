import pandas as pd
import numpy as np
import geopandas as gpd
from tidyzoning import find_district_idx
from tidyzoning import check_land_use

def check_zoning_process(tidybuilding, tidyzoning, tidyparcel, check_func):
    """
    CHeck our tidybuilding in all tidyzonings and corresponding parcels

    Parameters:
    tidybuilding (pd.DataFrame): DataFrame containing building information.
    tidyzoning (pd.DataFrame): DataFrame containing zoning information.
    tidyparcel (pd.DataFrame): DataFrame containing parcel information.
    check_func (function): Function to the certain constraints.

    Returns:
    pd.DataFrame: DataFrame with computed factors.
    
    How to use:
    check_fl_area_result_all = check_zoning_process(tidybuilding_4_fam, tidyzoning, tidyparcel, check_fl_area)
    """
    # Step 1: Perform land use check
    check_land_use_results = check_land_use(tidybuilding, tidyzoning)
    allowed_zoning_ids = check_land_use_results[check_land_use_results['allowed'] == True]['zoning_id'].unique()
    
    # Filter tidyzoning based on allowed zoning IDs
    tidyzoning_filtered = tidyzoning[tidyzoning.index.isin(allowed_zoning_ids)]
    
    # Step 2: Compute the different check functions
    all_results = []
    for _, row in tidyparcel():
        prop_id = row['Prop_ID']
        parcel_id = row['parcel_id']
        zoning_idx = row['zoning_id']
        filtered_tidyparcel = tidyparcel[(tidyparcel['parcel_id'] == parcel_id) & (tidyparcel['Prop_ID'] == prop_id)]
        filtered_tidyzoning = tidyzoning_filtered.loc[[zoning_idx]]
        results = check_func(tidybuilding, filtered_tidyzoning, filtered_tidyparcel)
        results["parcel_id"] = parcel_id  
        results["Prop_ID"] = prop_id
        all_results.append(results)
    
    return pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()