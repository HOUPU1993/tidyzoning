import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json
import time

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

def zoning_analysis_pipeline(
    tidybuilding,
    tidyzoning,
    tidyparcel_dims,
    tidyparcel_geo,
    detailed_check = False,
    run_check_land_use = True,
    run_check_height = True,
    run_check_height_eave  = True,
    run_check_stories = True,
    run_check_unit_size = True,
    run_check_far = True,
    run_check_unit_density = True,
    run_check_lot_coverage = True,
    run_check_fl_area = True,
    run_check_unit_qty = True,
    run_check_footprint = False
):
    
    total_start = time.time()

    if tidyparcel_geo is None and run_check_footprint == True:
        print("No parcel side geometry given. Skipping check_fooprint function.")
    
    # Initialize parcel table
    tidyparcel_df = tidyparcel_dims.copy()
    tidyparcel_df['false_reasons'] = None
    tidyparcel_df['maybe_reasons'] = None

    check_cols = ['check_land_use', 'check_height', 'check_height_eave', 'check_stories','check_unit_size', 'check_far', 'check_unit_density', 'check_lot_coverage','check_fl_area', 'check_unit_qty']
    for col in check_cols:
        tidyparcel_df[col] = pd.Series(index=tidyparcel_df.index, dtype='object')
        
    false_dfs = []

    # 1) Land use check
    if run_check_land_use:
        lu_start = time.time()
        lu_df = check_land_use(tidybuilding, tidyzoning)
        allowed_zones = set(lu_df.loc[lu_df['allowed'], 'zoning_id'])
        tidyparcel_df['check_land_use'] = tidyparcel_df['zoning_id'].isin(allowed_zones)
        # print the infomation
        total = len(tidyparcel_df)
        n_allowed = tidyparcel_df['check_land_use'].sum()
        pct_allowed = (n_allowed / total * 100) if total else 0
        print(f"check_land_use: {n_allowed} / {total} parcels allowed ({pct_allowed:.1f}%)")
        print(f"check_land_use runtime: {time.time() - lu_start:.1f} sec")
        
        if not detailed_check:
            mask_fail = ~tidyparcel_df['check_land_use']
            df_fail = tidyparcel_df[mask_fail].copy()
            df_fail['false_reasons'] = 'check_land_use'
            false_dfs.append(df_fail)
            tidyparcel_df = tidyparcel_df[~mask_fail].copy()


    # Mapping of other checks    
    # 1) map each check‐name to the actual function
    check_map = {
        'check_height':         check_height,
        'check_height_eave':    check_height_eave,
        'check_stories':        check_stories,
        'check_unit_size':      check_unit_size,
        'check_far':            check_far,
        'check_unit_density':   check_unit_density,
        'check_lot_coverage':   check_lot_coverage,
        'check_fl_area':        check_fl_area,
        'check_unit_qty':       check_unit_qty,
    }

    # 2) map each check‐name to its run_ flag
    run_map = {
        'check_height':         run_check_height,
        'check_height_eave':    run_check_height_eave,
        'check_stories':        run_check_stories,
        'check_unit_size':      run_check_unit_size,
        'check_far':            run_check_far,
        'check_unit_density':   run_check_unit_density,
        'check_lot_coverage':   run_check_lot_coverage,
        'check_fl_area':        run_check_fl_area,
        'check_unit_qty':       run_check_unit_qty,
    }

    baseline_n  = len(tidyparcel_df)
    
    # 2) Sequential checks
    for name, func in check_map.items():
        if run_map.get(name, False):
            start = time.time()
            for idx, row in tqdm(
                tidyparcel_df.iterrows(),
                total=len(tidyparcel_df),
                desc=f"Running {name}"
            ):
                # pull out the single‐row parcel & its district
                zoning_idx = row['zoning_id']
                row_parcel = tidyparcel_df.loc[[idx]]
                row_zoning = tidyzoning[tidyzoning['zoning_id'] == zoning_idx]
                try:
                    result_df = func(tidybuilding, row_zoning, row_parcel)
                    allowed_val = result_df['allowed'].iloc[0]
                except Exception:
                    allowed_val = 'MAYBE'
                # normalize anything weird into 'MAYBE'
                if allowed_val not in (True, False, 'MAYBE'):
                    allowed_val = 'MAYBE'
                # write back the result
                tidyparcel_df.at[idx, name] = allowed_val
                # update reason columns
                if allowed_val == 'MAYBE':
                    prev = tidyparcel_df.at[idx, 'maybe_reasons']
                    tidyparcel_df.at[idx, 'maybe_reasons'] = name if prev is None else f"{prev}, {name}"
                if allowed_val == False:
                    prev = tidyparcel_df.at[idx, 'false_reasons']
                    tidyparcel_df.at[idx, 'false_reasons'] = name if prev is None else f"{prev}, {name}"
            if not detailed_check:
                mask_fail = tidyparcel_df[name] == False
                df_fail = tidyparcel_df[mask_fail].copy()
                false_dfs.append(df_fail)
                tidyparcel_df = tidyparcel_df[~mask_fail].copy()
            # 1) how many parcels survive this check (True or MAYBE):
            n_remain = len(tidyparcel_df)
            pct_remain = n_remain / baseline_n * 100
            # 2) within those survivors, how many are True vs MAYBE for this check:
            vc      = tidyparcel_df[name].value_counts(dropna=False)
            n_true  = vc.get(True,   0)
            n_false  = vc.get(False,  0)
            n_maybe = vc.get('MAYBE', 0)
            pct_true  = n_true  / baseline_n * 100
            pct_false = n_false / baseline_n * 100
            pct_maybe = n_maybe / baseline_n * 100
            # 3) print it all out:
            print(f"{name:20s}  "
                f"Survive: {n_remain:4d}/{baseline_n:4d} ({pct_remain:5.1f}%)"
                f"True: {n_true:4d} ({pct_true:5.1f}%)"
                f"MAYBE: {n_maybe:4d} ({pct_maybe:5.1f}%)"
                f"False: {n_false:4d} ({pct_false:5.1f}%)")
            print(f"{name} runtime: {time.time() - start:.1f} sec")

    # 4) Combine and summarize
    initial_df = pd.concat(false_dfs + [tidyparcel_df], ignore_index=True)
    check_cols = [c for c in initial_df.columns if c.startswith('check_')]
    initial_df['has_false'] = initial_df[check_cols].eq(False).sum(axis=1)
    initial_df['has_maybe'] = initial_df[check_cols].eq('MAYBE').sum(axis=1)
    initial_df['allowed'] = initial_df.apply(
        lambda r: False if r['has_false'] > 0 else ('MAYBE' if r['has_maybe'] > 0 else True), axis=1
    )
    def format_initial_reason(row):
        parts = []
        fr = row.get('false_reasons') or ""
        mr = row.get('maybe_reasons') or ""
        if fr:
            parts.append(f"FALSE encountered: {fr}")
        if mr:
            parts.append(f"MAYBE encountered: {mr}")
        return " - ".join(parts) if parts else "parcels allow the building"
    initial_df['reason'] = initial_df.apply(format_initial_reason, axis=1)

    # 3) Footprint check
    if run_check_footprint:
        fp_start = time.time()
        # only parcels still allowed or MAYBE
        initial_df['check_footprint'] = pd.Series(index=initial_df.index, dtype='object')
        to_run = initial_df[initial_df['allowed'].isin([True, 'MAYBE']) & (initial_df['confidence'] == 'confidence_parcel')]
        print(f"Running check_footprint on {len(to_run)}/{baseline_n} parcels")
        
        for idx, row in tqdm(
            to_run.iterrows(),
            total=len(to_run),
            desc="check_footprint"
        ):
            # remember what it was before
            orig_allowed = initial_df.at[idx, 'allowed']
            # find the each parcel and corresponding zoning id
            pid = row['parcel_id']
            zidx = row['zoning_id']
            # get the parcel dims & geo
            parcel_dim = tidyparcel_dims[tidyparcel_dims['parcel_id']==pid]
            parcel_geo = tidyparcel_geo[tidyparcel_geo['parcel_id']==pid]
            zoning_row = tidyzoning.loc[[zidx]]
            
            # 3a) quick area check
            bld_fp = tidybuilding['footprint'].iat[0]
            lot_ac = parcel_dim['lot_area'].iat[0]
            if bld_fp > lot_ac * 43560:
                ok = False
            else:
                # 3b) full geometric check
                try:
                    sb = add_setbacks(tidybuilding, zoning_row, parcel_dim, parcel_geo)
                    ba = get_buildable_area(sb)
                    fp_res = check_footprint(ba, tidybuilding)
                    ok = 'MAYBE' if fp_res.empty else fp_res['allowed'].iat[0]
                except Exception:
                    ok = 'MAYBE'

            initial_df.at[idx, 'check_footprint'] = ok
            if ok == False:
                prev = initial_df.at[idx, 'false_reasons']
                initial_df.at[idx, 'false_reasons'] = ("check_footprint" if prev is None else f"{prev}, check_footprint")
                initial_df.at[idx, 'allowed'] = False
            elif ok == 'MAYBE':
                prev = initial_df.at[idx, 'maybe_reasons']
                initial_df.at[idx, 'maybe_reasons'] = ("check_footprint" if prev is None else f"{prev}, check_footprint")
            else:  # ok == True
                if orig_allowed == 'MAYBE':
                    # keep the overall allowed=MAYBE
                    prev = initial_df.at[idx, 'maybe_reasons']
                    initial_df.at[idx, 'maybe_reasons'] = ("footprint check passed, but exist MAYBE in the constraints check" if prev is None
                        else f"{prev}, footprint check passed, but exist MAYBE in the constraints check"
                    )
                if orig_allowed == True:
                    initial_df.at[idx, 'reason'] = "parcels fit the building"
        print(f"check_footprint runtime: {time.time() - fp_start:.1f} sec")

    # 5) Combine and summarize
    final_df = initial_df.copy()
    if run_check_footprint:
        def format_footprint_reason(row):
            parts = []
            fr = row.get('false_reasons') or ""
            mr = row.get('maybe_reasons') or ""
            if fr:
                parts.append(f"FALSE encountered: {fr}")
            if mr:
                parts.append(f"MAYBE encountered: {mr}")
            return " - ".join(parts) if parts else row['reason']
        final_df['reason'] = final_df.apply(format_footprint_reason, axis=1)

    # Cleanup
    # drop_cols = ['false_reasons', 'maybe_reasons'] + (check_cols if not detailed_check else [])
    drop_cols = ['false_reasons', 'maybe_reasons']
    final_df.drop(columns=drop_cols, inplace=True, errors='ignore')
    print(f"zoning_analysis_pipeline total runtime: {time.time() - total_start:.1f} sec")
    if run_check_footprint:
        print(f"{(final_df['allowed'] == True).sum()} / {len(final_df)} parcels fit the building")
        print(f"{(final_df['allowed'] == 'MAYBE').sum()} / {len(final_df)} parcels maybe fit the building")
    else:
        print(f"{(final_df['allowed'] == True).sum()} / {len(final_df)} parcels allow the building")
        print(f"{(final_df['allowed'] == 'MAYBE').sum()} / {len(final_df)} parcels maybe allow the building")
    return final_df