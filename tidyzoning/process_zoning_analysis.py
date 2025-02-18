import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json

from shapely.geometry import Point
from shapely.geometry import box

# input my libraries
from tidyzoning import find_district_idx
from tidyzoning import find_bldg_type
from tidyzoning import check_land_use
from tidyzoning import get_zoning_req
from tidyzoning import check_fl_area
from tidyzoning import check_far
from tidyzoning import check_height
from tidyzoning import check_bedrooms
from tidyzoning import check_lot_coverage
from tidyzoning import check_unit_density
from tidyzoning import check_unit_size
from tidyzoning import add_setbacks
from tidyzoning import get_buildable_area
from tidyzoning.check_footprint import check_footprint

def process_zoning_analysis(tidybuilding, tidyzoning, tidyparcel):
    """
    Process building and zoning analysis, including different check funtions to find the allowed parcels based on certain building type,
    and utilizing add_setbacks(), get buildable area() to get the selected buildable area, and check footprint() is to check the fitted tidybuilding in the certain tidyparcel.
    """

    '''the general check functions'''
    # 1. different check funtions only need input tidybuilding and tidyzoning
    def get_consistent_zoning_ids(tidybuilding, tidyzoning):
        check_functions = [
            check_land_use,
            check_fl_area,
            check_height,
            check_bedrooms,
            check_unit_density,
            check_unit_size
        ]
        check_results = [func(tidybuilding, tidyzoning) for func in check_functions]
        
        # Merge check results
        merged_df = check_results[0]
        for df in check_results[1:]:
            merged_df = merged_df.merge(df, on='zoning_id', suffixes=('', '_other'))
        
        # Select all zoning_ids where all 'allowed' columns are True
        allowed_columns = [col for col in merged_df.columns if 'allowed' in col]
        return merged_df[merged_df[allowed_columns].all(axis=1)][['zoning_id']]

    consistent_zoning_ids = get_consistent_zoning_ids(tidybuilding, tidyzoning)

    '''filtered the corresponding parcels in selected zoning areas'''
    # 2. Filter tidyzoning
    tidyzoning_filtered = tidyzoning.loc[tidyzoning.index.isin(consistent_zoning_ids['zoning_id'])]

    # 3. Filer tidyparcels
    centroid_rows = tidyparcel[tidyparcel["side"] == "centroid"]
    sjoin_result = centroid_rows.sjoin(tidyzoning_filtered, predicate="intersects", how="inner")
    valid_parcel_ids = sjoin_result["parcel_id"].unique()
    tidyparcel_filtered = tidyparcel[tidyparcel["parcel_id"].isin(valid_parcel_ids)]

    '''filtered the corresponding parcels based on the check_far and check_lot_coverage function'''
    # 4. Calculate find_district_idx
    find_district_idx_results = find_district_idx(tidyparcel_filtered, tidyzoning_filtered)

    # 5. Calculate FAR and Lot Coverage
    def compute_factors(tidybuilding, tidyzoning_filtered, tidyparcel_filtered, check_func):
        all_results = []
        for _, row in find_district_idx_results.iterrows():
            prop_id = row['prop_id']
            zoning_idx = row['zoning_id']
            filtered_tidyparcel = tidyparcel_filtered[tidyparcel_filtered['Prop_ID'] == prop_id]
            filtered_tidyzoning = tidyzoning.iloc[[zoning_idx]]
            results = check_func(tidybuilding, filtered_tidyzoning, filtered_tidyparcel)
            all_results.append(results)
        return pd.concat(all_results, ignore_index=True)
    final_results_far = compute_factors(tidybuilding, tidyzoning_filtered, tidyparcel_filtered, check_far)
    final_results_lot_coverage = compute_factors(tidybuilding, tidyzoning_filtered, tidyparcel_filtered, check_lot_coverage)

    # 6. Merge FAR and Lot Coverage results
    check_merge_far_lot_coverage = final_results_lot_coverage.merge(
        final_results_far, left_index=True, right_index=True, suffixes=['', '_right']
    )
    check_merge_far_lot_coverage = check_merge_far_lot_coverage[
        (check_merge_far_lot_coverage['allowed'] == True) & (check_merge_far_lot_coverage['allowed_right'] == True)
    ]
    check_merge_far_lot_coverage = check_merge_far_lot_coverage[final_results_lot_coverage.columns]

    # 7. Update tidyparcel_filtered
    tidyparcel_filtered = tidyparcel_filtered.merge(check_merge_far_lot_coverage[['Prop_ID', 'allowed']], on='Prop_ID', how='left')
    tidyparcel_filtered = tidyparcel_filtered[tidyparcel_filtered['allowed'] == True]
    tidyparcel_filtered = tidyparcel_filtered.drop_duplicates(subset=['geometry'], keep='first')

    '''get buildable area for rach parcel based on setback info'''
    # 8. Calculate Setbacks
    final_results_setbacks = compute_factors(tidybuilding, tidyzoning_filtered, tidyparcel_filtered, add_setbacks)
    final_results_setbacks = final_results_setbacks.drop_duplicates(subset=['geometry'], keep='first')

    # 9. Calculate buildable area
    final_results_buildable_area = get_buildable_area(final_results_setbacks)
    final_results_buildable_area = final_results_buildable_area.drop_duplicates(subset=['buildable_geometry'], keep='first')

    # 10. Calculate building footprint
    check_footprint_results = check_footprint(final_results_buildable_area, tidybuilding)

    '''Print analysis results'''
    total_parcels = len(tidyparcel['parcel_id'].unique())
    total_allowed_parcels = len(check_footprint_results['Prop_ID'].unique())
    total_fitted_parcels = (check_footprint_results.loc[:, check_footprint_results.columns != 'Prop_ID'] == True).sum().sum()
    percent_fitted_in_allowed = total_fitted_parcels / total_allowed_parcels if total_allowed_parcels > 0 else 0
    percent_fitted_in_total = total_fitted_parcels / total_parcels if total_parcels > 0 else 0

    print(f"Total parcels: {total_parcels}")
    print(f"Total allowed parcels: {total_allowed_parcels}")
    print(f"Total fitted parcels: {total_fitted_parcels}")
    print(f"Percentage of fitted parcels in total allowed parcels: {percent_fitted_in_allowed:.2%}")
    print(f"Percentage of fitted parcels in total parcels: {percent_fitted_in_total:.2%}")

    return check_footprint_results