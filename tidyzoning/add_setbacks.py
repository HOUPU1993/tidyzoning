import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from tidyzoning import get_zoning_req

def add_setbacks(tidybuilding, tidyzoning, tidyparcel):
    """
    Add setbacks to each tidyparcel based on tidyzoning requirement.

    Parameters:
    ----------
    tidybuilding : A GeoDataFrame containing information about a single building. 
    tidyparcel : A GeoDataFrame containing information about the tidyparcels(single/multiple ). 
    tidyzoning : A GeoDataFrame containing zoning constraints. It may have multiple rows,

    Returns:
    -------
    DataFrame
        Add two columns in tidyparcel geodataframe: setback & units
    """
    
    # filter centriod and nan value in side column
    tidyparcel = tidyparcel[(tidyparcel['side'].notna()) & (tidyparcel['side'] != 'centroid')].copy()
    # Initialize columns for setbacks and units
    tidyparcel['setback'] = None
    tidyparcel['unit'] = None

    
    # mapping the side classification name
    name_key = {
        'front': 'setback_front',
        'Interior side': 'setback_side_int',
        'Exterior side': 'setback_side_ext',
        'rear': 'setback_rear'
    }
    
    # Calculate FAR for each parcel_id
    for parcel_id, group in tidyparcel.groupby("parcel_id"):
        # Iterate through each row in tidyzoning
        for index, zoning_row in tidyzoning.iterrows():
            zoning_req = get_zoning_req(tidybuilding, zoning_row.to_frame().T)  # ✅ Fix the issue of passing Series

            # If no zoning constraints exist, leave setbacks and units as None
            if zoning_req is None or zoning_req.empty:
                continue

            setbacks = []
            units = []
            
            for _, row in group.iterrows():
                side_type = row['side']
                
                if side_type in name_key:
                    filtered_constraints = zoning_req[zoning_req['spec_type'] == name_key[side_type]]
                    
                    if not filtered_constraints.empty:
                        setback_value = filtered_constraints.iloc[0]['min_value']
                        unit_value = filtered_constraints.iloc[0]['unit']
                    else:
                        setback_value = None
                        unit_value = None
                else:
                    setback_value = None
                    unit_value = None
                
                setbacks.append(setback_value)
                units.append(unit_value)
            
            tidyparcel.loc[group.index, 'setback'] = setbacks
            tidyparcel.loc[group.index, 'unit'] = units
    
    return tidyparcel