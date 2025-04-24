import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union
from tidyzoning import get_zoning_req

def add_setbacks(tidybuilding, tidyzoning, tidyparcel, confident_tidyparcel, buffer_dist=5):
    """
    Add setbacks to each confident_tidyparcel side, including extra rules:
      - setback_dist_boundary
      - setback_side_sum
      - setback_front_sum

    Parameters:
    ----------
    tidybuilding : GeoDataFrame
    tidyzoning    : GeoDataFrame (with geometry for the district)
    tidyparcel    : GeoDataFrame (the parcel footprint)
    confident_tidyparcel : GeoDataFrame (parcel sides with 'side' and geometry)
    buffer_dist   : float (distance in same CRS units to buffer district boundary)

    Returns:
    -------
    GeoDataFrame (confident_tidyparcel) with columns:
      setback (float), unit (str), on_boundary (bool, if applicable)
    """
    # 1. Filter sides
    parcel_id = tidyparcel.iloc[0]["parcel_id"]
    sides = confident_tidyparcel[
        (confident_tidyparcel["parcel_id"] == parcel_id) &
        (confident_tidyparcel["side"].notna()) &
        (confident_tidyparcel["side"] != "centroid")
    ].copy()
    # init cols
    sides["setback"] = None
    sides["unit"]   = None
    sides["on_boundary"] = False

    name_key = {
        "front":          "setback_front",
        "Interior side":  "setback_side_int",
        "Exterior side":  "setback_side_ext",
        "rear":           "setback_rear"
    }

    # 2. Get all zoning requirements
    zoning_req = get_zoning_req(tidybuilding, tidyzoning, tidyparcel)
    if zoning_req is None or zoning_req.empty:
        return sides

    for idx, row in sides.iterrows():
        side_type = row["side"]
        if side_type in name_key:
            filt = zoning_req[zoning_req["spec_type"] == name_key[side_type]]
            # if not filt.empty:
            #     sides.at[idx, "setback"] = filt.iloc[0]["min_value"]
            #     sides.at[idx, "unit"]    = filt.iloc[0]["unit"]
            if not filt.empty:
                raw = filt.iloc[0]["min_value"]
                # sort if it’s a tuple, list or ndarray
                if isinstance(raw, tuple):
                    val = sorted(raw, reverse=True)
                elif isinstance(raw, list):
                    val = sorted(raw, reverse=True)
                elif isinstance(raw, np.ndarray):
                    val = sorted(raw, reverse=True)
                else:
                    # scalar or pint.Quantity, leave as is
                    val = raw

                sides.at[idx, "setback"] = val
                sides.at[idx, "unit"] = filt.iloc[0]["unit"]

    # 4. Extra‐rule: distance to boundary
    if "setback_dist_boundary" in zoning_req["spec_type"].values:
        dist_b = float(zoning_req.loc[zoning_req["spec_type"] == "setback_dist_boundary", "min_value"].iloc[0])
        # extract district boundary as MultiLineString
        boundary = unary_union(tidyzoning.geometry.values).boundary
        buf = boundary.buffer(buffer_dist)
        # mark sides on boundary
        on_b = sides.geometry.within(buf)
        sides.loc[on_b, "on_boundary"] = True
        # enforce minimum
        sides.loc[on_b, "setback"] = np.maximum(sides.loc[on_b, "setback"], dist_b)

    # 5. Extra‐rule: side‐sum
    if "setback_side_sum" in zoning_req["spec_type"].values:
        side_sum = float(zoning_req.loc[zoning_req["spec_type"] == "setback_side_sum", "min_value"].iloc[0])
        # get indexes for interior & exterior
        int_idx = list(sides[sides.side=="Interior side"].index)
        ext_idx = list(sides[sides.side=="Exterior side"].index)
        # need two edges
        if len(int_idx)>=1 and len(ext_idx)>=1:
            idx_ext, idx_int = ext_idx[0], int_idx[0]
        elif len(int_idx)>=2:
            idx_ext, idx_int = int_idx[0], int_idx[1]
        elif len(ext_idx)>=2:
            idx_ext, idx_int = ext_idx[0], ext_idx[1]
        else:
            # not enough edges → skip side‐sum rule
            idx_ext = idx_int = None
        if idx_ext is not None:
            v_ext, v_int = sides.at[idx_ext,"setback"], sides.at[idx_int,"setback"]
            extra = max(0, side_sum - (v_ext + v_int))
            # UPDATE ALL interior‐side rows at once
            int_mask = sides.side == "Interior side"
            sides.loc[int_mask, "setback"] = sides.loc[int_mask, "setback"] + extra

    # 6. Extra‐rule: front/rear sum
    if "setback_front_sum" in zoning_req["spec_type"].values:
        front_sum = float(zoning_req.loc[zoning_req["spec_type"] == "setback_front_sum", "min_value"].iloc[0])
        f_idx = list(sides[sides.side == "front"].index)
        r_idx = list(sides[sides.side == "rear"].index)
        if len(f_idx)>=1 and len(r_idx)>=1:
            idx_f, idx_r = f_idx[0], r_idx[0]
            vf, vr = sides.at[idx_f,"setback"], sides.at[idx_r,"setback"]
            extra = max(0, front_sum - (vf + vr))
            # UPDATE ALL rear‐side rows at once
            rear_mask = sides.side == "rear"
            sides.loc[rear_mask, "setback"] = sides.loc[rear_mask, "setback"] + extra
        else:
        # not enough edges → skip front‐rear sum rule
            pass
    
    return sides