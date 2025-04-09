import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json

from shapely.geometry import Point
from shapely.geometry import box

from joblib import Parallel, delayed
from tqdm import tqdm

# input my libraries
from tidyzoning import find_district_idx
from tidyzoning import find_bldg_type
from tidyzoning import check_land_use
from tidyzoning import get_zoning_req
from tidyzoning import check_fl_area
from tidyzoning import check_far
from tidyzoning import check_height
from tidyzoning import check_stories
from tidyzoning import check_bedrooms
from tidyzoning import check_lot_coverage
from tidyzoning import check_unit_density
from tidyzoning import check_height_eave
from tidyzoning import check_unit_qty
from tidyzoning import add_setbacks
from tidyzoning import get_buildable_area
from tidyzoning import unify_tidybuilding
from tidyzoning import filter_constraints
from tidyzoning import check_zoning_process
from tidyzoning import parcels_in_zoning
from tidyzoning import parcel_in_confidence
from tidyzoning import generate_parcel_info

from tidyzoning.check_footprint import check_footprint
from tidyzoning.check_unit_size import check_unit_size

def zoning_analysis_pipeline(tidybuilding, tidyzoning, tidyparcel, confident_tidyparcel, n_jobs=-1):
    """
    Process each parcel with the following steps:
    
    Step 1: Perform a land use check:
      - Use check_land_use on tidyzoning to pre-filter and obtain zoning_ids with allowed == True.
    
    Step 2: Filter tidyzoning and tidyparcel based on allowed zoning_ids.
            Only the parcels that pass the land use check will be processed further.
            Also, add a "row_id" column to preserve the original order.
    
    Step 3: For each parcel that passed the land use check, execute the following check functions sequentially:
         - check_height
         - check_stories
         - check_unit_size
         - check_far
         - check_unit_density
         - check_bedrooms
         - check_lot_coverage
         - check_fl_area
         - check_height_eave
         - check_unit_qty
         
         Checking logic for subsequent checks:
           - Execute each check function sequentially.
           - If any function returns False, immediately stop further checks; set allowed to False and the reason to that check's name.
           - If a function returns "MAYBE", record that check's name (and continue checking).
           - If all checks return True, then allowed is True with reason "Our tidybuilding is allowed".
           - If no check returned False but at least one returned "MAYBE", then final allowed is "MAYBE" and the reason is a comma-separated list of the check names.
    
    Step 4: For parcels that failed the land use check, create default rows with allowed==False,
            reason "check_land_use", and check_process {"check_land_use": False}.
    
    Step 5: Combine the two groups and sort by the original parcel order.
    
    Step 6: Further process those rows where allowed==True by:
         - Calling add_setbacks, get_buildable_area, and check_footprint.
         - If check_footprint returns allowed==False, update allowed to False and reason to "check_footprint";
         - If check_footprint returns allowed==True, update reason from "Our tidybuilding is allowed" to "Our tidybuilding is fitted".
         Moreover,如果原有 allowed 为 "MAYBE" 且进一步处理后 allowed 为 True，则仍保留 "MAYBE"，并将 reason 改为 "please review the check_process".
    
    Parameters:
        tidybuilding (pd.DataFrame): Building information dataset.
        tidyzoning (pd.DataFrame): Zoning information dataset, indexed by zoning_id.
        tidyparcel (pd.DataFrame): Parcel information dataset; must include 'zoning_id', 'Prop_ID', 'parcel_id'.
        confident_tidyparcel (pd.DataFrame): A parcel dataset with the same 'parcel_id's as tidyparcel.
        n_jobs (int): Number of parallel tasks; -1 uses all available CPUs.
    
    Returns:
        pd.DataFrame: The final DataFrame after all processing, with reset index.
    """
    # -----------------------------
    # Steps 1-5: Initial processing.
    # -----------------------------
    # Step 1: Land use check.
    check_land_use_results = check_land_use(tidybuilding, tidyzoning)
    allowed_zoning_ids = check_land_use_results[check_land_use_results['allowed'] == True]['zoning_id'].unique()

    # Filter tidyzoning based on allowed zoning_ids.
    tidyzoning_filtered = tidyzoning[tidyzoning.index.isin(allowed_zoning_ids)]

    # Split tidyparcel into those that passed and failed the land use check.
    allowed_parcels = tidyparcel[tidyparcel['zoning_id'].isin(allowed_zoning_ids)].copy()
    allowed_parcels["row_id"] = allowed_parcels.index
    disallowed_parcels = tidyparcel[~tidyparcel['zoning_id'].isin(allowed_zoning_ids)].copy()
    disallowed_parcels["row_id"] = disallowed_parcels.index

    total = len(tidyparcel)
    allowed_count = allowed_parcels.shape[0]
    percent = allowed_count / total * 100
    print(f"Parcel count: total {total} parcels,\n{allowed_count} passed land use check; others marked as check_land_use=False.\nPercentage remaining: {percent:.2f}%.")

    # Subsequent check functions.
    check_sequence = [
        ("check_height", check_height),
        ("check_stories", check_stories),
        ("check_unit_size", check_unit_size),
        ("check_far", check_far),
        ("check_unit_density", check_unit_density),
        ("check_bedrooms", check_bedrooms),
        ("check_lot_coverage", check_lot_coverage),
        ("check_fl_area", check_fl_area),
        ("check_height_eave", check_height_eave),
        ("check_unit_qty", check_unit_qty)
    ]

    def process_allowed_parcel(row):
        """
        Process one allowed parcel through the check_sequence.
        """
        prop_id = row['Prop_ID']
        parcel_id = row['parcel_id']
        zoning_idx = row['zoning_id']
        row_id = row['row_id']

        # Create a single-row DataFrame for processing.
        filtered_parcel = pd.DataFrame([row])
        try:
            filtered_zoning = tidyzoning_filtered.loc[[zoning_idx]]
        except KeyError:
            return {
                "Prop_ID": prop_id,
                "parcel_id": parcel_id,
                "zoning_id": zoning_idx,
                "allowed": False,
                "reason": "zoning id not found",
                "check_process": {"check_land_use": True},
                "row_id": row_id
            }

        # Record that the land use check passed.
        check_process = {"check_land_use": True}
        maybe_checks = []
        false_reason = None

        # Execute each subsequent check function sequentially.
        for check_name, check_func in check_sequence:
            result_df = check_func(tidybuilding, filtered_zoning, filtered_parcel)
            allowed_val = result_df['allowed'].iloc[0]
            check_process[check_name] = allowed_val

            # If a check returns False, immediately stop further checks.
            if allowed_val == False:
                false_reason = check_name
                break
            elif allowed_val == "MAYBE":
                maybe_checks.append(check_name)

        # Determine final allowed status and reason.
        if false_reason is not None:
            final_allowed = False
            reason = false_reason
        elif maybe_checks:
            final_allowed = "MAYBE"
            reason = ", ".join(maybe_checks)
        else:
            final_allowed = True
            reason = "Our tidybuilding is allowed"

        return {
            "Prop_ID": prop_id,
            "parcel_id": parcel_id,
            "zoning_id": zoning_idx,
            "allowed": final_allowed,
            "reason": reason,
            "check_process": check_process,
            "row_id": row_id
        }

    # Process allowed parcels in parallel.
    from joblib import Parallel, delayed
    allowed_results = Parallel(n_jobs=n_jobs)(
        delayed(process_allowed_parcel)(row)
        for _, row in tqdm(allowed_parcels.iterrows(), total=allowed_parcels.shape[0], desc="Processing Allowed Parcels")
    )
    allowed_df = pd.DataFrame(allowed_results)

    # For parcels that failed the land use check, create default result rows.
    disallowed_results = []
    for _, row in disallowed_parcels.iterrows():
        prop_id = row['Prop_ID']
        parcel_id = row['parcel_id']
        zoning_idx = row['zoning_id']
        row_id = row['row_id']
        disallowed_results.append({
            "Prop_ID": prop_id,
            "parcel_id": parcel_id,
            "zoning_id": zoning_idx,
            "allowed": False,
            "reason": "check_land_use",
            "check_process": {"check_land_use": False},
            "row_id": row_id
        })
    disallowed_df = pd.DataFrame(disallowed_results)

    # Combine allowed and disallowed results and restore original order.
    intermediate_df = pd.concat([allowed_df, disallowed_df], ignore_index=True)
    intermediate_df = intermediate_df.sort_values("row_id").drop(columns="row_id")
    
    # -----------------------------
    # Step 6: Further processing for allowed parcels.
    # -----------------------------
    def process_further(row):
        """
        For a row with allowed == True, further process the parcel using:
            add_setbacks, get_buildable_area, and check_footprint.
        Updates the row based on check_footprint results.
        """
        parcel_id = row['parcel_id']
        zoning_idx = row['zoning_id']

        # Get the corresponding parcel row from tidyparcel.
        parcel_row = tidyparcel[tidyparcel['parcel_id'] == parcel_id]
        # Get the corresponding row from confident_tidyparcel.
        confident_parcel_row = confident_tidyparcel[confident_tidyparcel['parcel_id'] == parcel_id]
        # Get zoning row from tidyzoning.
        try:
            zoning_row = tidyzoning.loc[[zoning_idx]]
        except KeyError:
            cp = row['check_process']
            cp['check_footprint'] = False
            row['allowed'] = False
            row['reason'] = "zoning id not found"
            row['check_process'] = cp
            return row

        # Call the additional functions (each operating on a single parcel).
        add_setbacks_results = add_setbacks(tidybuilding, zoning_row, parcel_row, confident_parcel_row)
        buildable_area_result = get_buildable_area(add_setbacks_results)
        footprint_results = check_footprint(buildable_area_result, tidybuilding)
        if footprint_results.empty:
            footprint_allowed = False  # or some default behavior
        else:
            footprint_allowed = footprint_results['allowed'].iloc[0]

        # Update check_process to record the check_footprint result.
        cp = row['check_process']
        cp['check_footprint'] = footprint_allowed

        # If the original allowed is MAYBE and the further processing result is True, retain MAYBE and update the reason to "please review the check_process"
        if row['allowed'] == "MAYBE" and footprint_allowed == True:
            row['allowed'] = "MAYBE"
            row['reason'] = "please review the check_process"
        else:
            if footprint_allowed == False:
                row['allowed'] = False
                row['reason'] = "check_footprint"
            else:
                row['allowed'] = True
                row['reason'] = "Our tidybuilding is fitted"
        row['check_process'] = cp
        return row

    # Sequentially process records in intermediate_df where allowed is True or "MAYBE".
    df_to_further = intermediate_df[intermediate_df['allowed'].isin([True, "MAYBE"])].copy()
    print(f"Number of parcels to run check_footprint after passing previous checks: {df_to_further.shape[0]} ({df_to_further.shape[0]/len(tidyparcel)*100:.2f}% of total parcels)")
    
    further_results = []
    for _, row in tqdm(df_to_further.iterrows(), total=df_to_further.shape[0], desc="Processing Further Checks"):
        further_results.append(process_further(row))
    further_df = pd.DataFrame(further_results)

    # Update the corresponding allowed, reason, and check_process in intermediate_df
    # Iterate through each row in further_df and update final_df based on parcel_id
    for _, row in further_df.iterrows():
        mask = (intermediate_df['parcel_id'] == row['parcel_id'])
        # Get the original allowed value
        orig_allowed = intermediate_df.loc[mask, 'allowed'].iloc[0]
        # If the original allowed is "MAYBE" and the corresponding allowed in further_df is True,
        # retain "MAYBE" and update the reason
        if orig_allowed == "MAYBE" and row['allowed'] == True:
            intermediate_df.loc[mask, 'allowed'] = "MAYBE"
            intermediate_df.loc[mask, 'reason'] = "please review the check_process"
            intermediate_df.loc[mask, ['Prop_ID', 'parcel_id', 'zoning_id', 'check_process']] = row[['Prop_ID', 'parcel_id', 'zoning_id', 'check_process']].values
        else:
            # Otherwise, directly replace with the corresponding values from further_df
            intermediate_df.loc[mask, ['Prop_ID', 'parcel_id', 'zoning_id', 'allowed', 'reason', 'check_process']] = row[['Prop_ID', 'parcel_id', 'zoning_id', 'allowed', 'reason', 'check_process']].values

    return intermediate_df.reset_index(drop=True)