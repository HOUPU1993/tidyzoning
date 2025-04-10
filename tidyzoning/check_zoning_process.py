import pandas as pd
import numpy as np
import geopandas as gpd
from tidyzoning import find_district_idx
from tidyzoning import check_land_use
from tqdm import tqdm
from joblib import Parallel, delayed

def check_zoning_process(tidybuilding, tidyzoning, tidyparcel, check_func, n_jobs=-1):
    """
    Updated check_zoning_process function with an optimized flow:

      1. A row_id is assigned to tidyparcel to preserve the original order.
      2. Land use is checked to extract allowed zoning IDs.
      3. Parcels are split into two groups:
         - Allowed parcels: those whose zoning IDs are in allowed_zoning_ids.
         - Disallowed parcels: those whose zoning IDs are not allowed.
      4. Allowed parcels are processed in parallel via check_func.
      5. For disallowed parcels, a DataFrame is explicitly built that includes:
         - zoning_id, parcel_id, Prop_ID, row_id from the original parcels.
         - 'allowed' is set to False.
         - 'constraint_min_note' and 'constraint_max_note' are fixed as "false by check_land_use".
      6. Finally, both results are concatenated and sorted by row_id to maintain the original order.

    Parameters:
      tidybuilding (pd.DataFrame): DataFrame containing building information.
      tidyzoning (pd.DataFrame): DataFrame containing zoning information.
      tidyparcel (pd.DataFrame): DataFrame containing parcel information.
      check_func (function): Function to check constraints.
      n_jobs (int): Number of parallel jobs (-1 uses all available CPUs).

    Returns:
      pd.DataFrame: A DataFrame with columns:
                  zoning_id, allowed, constraint_min_note, constraint_max_note,
                  parcel_id, Prop_ID,
                  preserving the original parcel order.
    """
    # Make a copy of tidyparcel and add a row_id column to preserve the original order.
    tidyparcel = tidyparcel.copy()
    tidyparcel["row_id"] = tidyparcel.index

    # Step 1: Perform land use check to obtain allowed zoning IDs.
    check_land_use_results = check_land_use(tidybuilding, tidyzoning)
    allowed_zoning_ids = check_land_use_results[check_land_use_results['allowed'] == True]['zoning_id'].unique()

    # Step 2: Split parcels into allowed and disallowed groups.
    allowed_parcels = tidyparcel[tidyparcel['zoning_id'].isin(allowed_zoning_ids)].reset_index(drop=True)
    disallowed_parcels = tidyparcel[~tidyparcel['zoning_id'].isin(allowed_zoning_ids)].reset_index(drop=True)
    
    # For allowed parcels, filter tidyzoning to include only allowed zones.
    tidyzoning_allowed = tidyzoning.loc[allowed_zoning_ids]
    
    # Step 3: Define a function to process allowed parcels.
    def process_allowed_parcel(row):
        prop_id = row['Prop_ID']
        parcel_id = row['parcel_id']
        zoning_idx = row['zoning_id']
        row_id = row['row_id']
        
        # Filter allowed_parcels for the current parcel.
        filtered_tidyparcel = allowed_parcels[
            (allowed_parcels['parcel_id'] == parcel_id) &
            (allowed_parcels['Prop_ID'] == prop_id)
        ]
        # Filter the tidyzoning_allowed for the current zoning.
        filtered_tidyzoning = tidyzoning_allowed.loc[[zoning_idx]]
        
        # Execute the provided check function.
        results = check_func(tidybuilding, filtered_tidyzoning, filtered_tidyparcel)
        # Append parcel-specific information.
        results["parcel_id"] = parcel_id
        results["Prop_ID"] = prop_id
        results["row_id"] = row_id
        return results

    # Step 4: Process allowed parcels in parallel with a progress bar.
    allowed_results = Parallel(n_jobs=n_jobs)(
        delayed(process_allowed_parcel)(row)
        for _, row in tqdm(allowed_parcels.iterrows(), total=allowed_parcels.shape[0], desc="Processing Allowed Parcels")
    )
    
    if allowed_results:
        allowed_df = pd.concat(allowed_results, ignore_index=True)
    else:
        allowed_df = pd.DataFrame()

    # Step 5: For disallowed parcels, directly build a DataFrame with the required fields.
    if not disallowed_parcels.empty:
        disallowed_df = pd.DataFrame({
            "zoning_id": disallowed_parcels["zoning_id"],
            "allowed": True,  # Boolean False
            "constraint_min_note": "false by check_land_use",
            "constraint_max_note": "false by check_land_use",
            "parcel_id": disallowed_parcels["parcel_id"],
            "Prop_ID": disallowed_parcels["Prop_ID"],
            "row_id": disallowed_parcels["row_id"]
        })
    else:
        disallowed_df = pd.DataFrame()

    # Step 6: Combine allowed and disallowed results and sort by row_id to preserve the original order.
    final_df = pd.concat([allowed_df, disallowed_df], ignore_index=True)
    final_df_sorted = final_df.sort_values("row_id").drop(columns="row_id")
    return final_df_sorted