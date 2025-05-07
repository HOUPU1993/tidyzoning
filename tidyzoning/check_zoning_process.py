import pandas as pd
import numpy as np
import geopandas as gpd
from tidyzoning import check_land_use
from tidyzoning import find_district_idx
from tqdm import tqdm
from joblib import Parallel, delayed

def check_zoning_process(tidybuilding, tidyzoning, tidyparcel, check_func, n_jobs=-1):
    """
    Check our tidybuilding in all tidyzonings and corresponding parcels

    Parameters:
    tidybuilding (pd.DataFrame): DataFrame containing building information.
    tidyzoning (pd.DataFrame): DataFrame containing zoning information.
    tidyparcel (pd.DataFrame): DataFrame containing parcel information.
    check_func (function): Function to check certain constraints.
    n_jobs (int): Number of parallel jobs (-1 means use all CPUs).

    Returns:
    pd.DataFrame: DataFrame with computed factors, preserving original parcel order.
    """
    # Step 1: Perform land use check
    check_land_use_results = check_land_use(tidybuilding, tidyzoning)
    allowed_zoning_ids = check_land_use_results[check_land_use_results['allowed'] == True]['zoning_id'].unique()

    # Step 2: Filter tidyzoning based on allowed zoning IDs
    tidyzoning_filtered = tidyzoning[tidyzoning.index.isin(allowed_zoning_ids)]

    # Step 3: Filter tidyparcel based on allowed zoning IDs and add row_id
    zoning_id = find_district_idx(tidyparcel,tidyzoning)
    tidyparcel_dim = tidyparcel[tidyparcel['side'] == 'centroid'] # for the parcel_id, it is still unique
    tidyparcel_dim_z = tidyparcel_dim.merge(zoning_id[['parcel_id','zoning_id']], on ='parcel_id', how = 'right') # for the parcel_id, maybe not unique
    
    tidyparcel_filtered = tidyparcel_dim_z[tidyparcel_dim_z['zoning_id'].isin(tidyzoning_filtered.index)].reset_index(drop=True)
    tidyparcel_filtered["row_id"] = tidyparcel_filtered.index

    # Step 4: Define processing function for one row
    def process_one_parcel(row):
        parcel_id = row['parcel_id']
        zoning_idx = row['zoning_id']
        row_id = row['row_id']
        
        filtered_tidyzoning = tidyzoning_filtered[tidyzoning_filtered['zoning_id'] == zoning_idx]
        filtered_tidyparcel = tidyparcel_dim[tidyparcel_dim['parcel_id'] == parcel_id]
        
        results = check_func(tidybuilding, filtered_tidyzoning, filtered_tidyparcel)
        results["parcel_id"] = parcel_id
        results["row_id"] = row_id  # Add row_id for ordering
        return results

    # Step 5: Run in parallel with progress bar
    results = Parallel(n_jobs=n_jobs)(
        delayed(process_one_parcel)(row)
        for _, row in tqdm(tidyparcel_filtered.iterrows(), total=tidyparcel_filtered.shape[0], desc="Parallel Processing")
    )

    # Step 6: Combine and sort results to maintain original parcel order
    if results:
        final_df = pd.concat(results, ignore_index=True)
        final_df_sorted = final_df.sort_values("row_id").drop(columns="row_id")
        return final_df_sorted
    else:
        return pd.DataFrame()