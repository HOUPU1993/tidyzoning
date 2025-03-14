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
    """
    # Step 1: Perform land use check
    check_land_use_results = check_land_use(tidybuilding, tidyzoning)
    allowed_zoning_ids = check_land_use_results[check_land_use_results['allowed'] == True]['zoning_id'].unique()
    
    # Filter tidyzoning based on allowed zoning IDs
    tidyzoning_filtered = tidyzoning[tidyzoning.index.isin(allowed_zoning_ids)]
    
    # Step 2: Filter tidyparcels based on centroid condition
    centroid_rows = tidyparcel[tidyparcel["side"] == "centroid"]
    sjoin_result = centroid_rows.sjoin(tidyzoning_filtered, predicate="intersects", how="inner")
    valid_parcel_ids = sjoin_result["parcel_id"].unique()
    tidyparcel_filtered = tidyparcel[tidyparcel["parcel_id"].isin(valid_parcel_ids)]
    
    # Step 3: Calculate find_district_idx
    find_district_idx_results = find_district_idx(tidyparcel_filtered, tidyzoning_filtered)
    
    # Step 4: Compute FAR and Lot Coverage
    all_results = []
    for _, row in find_district_idx_results.iterrows():
        parcel_id = row['parcel_id']
        zoning_idx = row['zoning_id']
        filtered_tidyparcel = tidyparcel_filtered[tidyparcel_filtered['parcel_id'] == parcel_id]
        filtered_tidyzoning = tidyzoning_filtered.loc[[zoning_idx]]
        results = check_func(tidybuilding, filtered_tidyzoning, filtered_tidyparcel)
        results["parcel_id"] = parcel_id  
        all_results.append(results)
    
    return pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()