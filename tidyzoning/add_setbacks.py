import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from tidyzoning import get_zoning_req

def add_setbacks(tidybuilding, tidyzoning, tidyparcel, confident_tidyparcel):
    """
    Add setbacks to each confident_tidyparcel based on tidyzoning requirements.

    Parameters:
    ----------
    tidybuilding : GeoDataFrame with a single building.
    tidyzoning : GeoDataFrame with one or more zoning constraints.
    tidyparcel : GeoDataFrame with one or more parcel rows.
    confident_tidyparcel : GeoDataFrame with parcel sides.

    Returns:
    -------
    GeoDataFrame with two new columns: 'setback' and 'unit'
    """

    # Extract IDs to filter
    prop_id = tidyparcel.iloc[0]["Prop_ID"]
    parcel_id = tidyparcel.iloc[0]["parcel_id"]

    # Filter for matching parcel and clean sides
    confident_tidyparcel = confident_tidyparcel[
        (confident_tidyparcel["Prop_ID"] == prop_id) &
        (confident_tidyparcel["parcel_id"] == parcel_id) &
        (confident_tidyparcel["side"].notna()) &
        (confident_tidyparcel["side"] != "centroid")
    ].copy()

    # Initialize columns
    confident_tidyparcel["setback"] = None
    confident_tidyparcel["unit"] = None

    # Mapping from side label to zoning spec_type
    name_key = {
        "front": "setback_front",
        "Interior side": "setback_side_int",
        "Exterior side": "setback_side_ext",
        "rear": "setback_rear"
    }

    # Loop through zoning rows
    for _, zoning_row in tidyzoning.iterrows():
        zoning_req = get_zoning_req(tidybuilding, zoning_row.to_frame().T, tidyparcel)
        if zoning_req is None or zoning_req.empty:
            continue

        # Apply setbacks per side
        for idx, row in confident_tidyparcel.iterrows():
            side_type = row["side"]
            if side_type in name_key:
                filtered_constraints = zoning_req[zoning_req["spec_type"] == name_key[side_type]]
                if not filtered_constraints.empty:
                    confident_tidyparcel.at[idx, "setback"] = filtered_constraints.iloc[0]["min_value"]
                    confident_tidyparcel.at[idx, "unit"] = filtered_constraints.iloc[0]["unit"]

    return confident_tidyparcel