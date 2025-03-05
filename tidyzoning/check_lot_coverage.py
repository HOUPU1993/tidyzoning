import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from tidyzoning import get_zoning_req

def check_lot_coverage(tidybuilding, tidyzoning, tidyparcel):
    """
    Checks whether the lot_coverage of a given building complies with zoning constraints.

    Parameters:
    ----------
    tidybuilding : A GeoDataFrame containing information about a single building. 
    tidyparcel : A GeoDataFrame containing information about the tidyparcels(single/multiple ). 
    tidyzoning : A GeoDataFrame containing zoning constraints. It may have multiple rows,

    Returns:
    -------
    DataFrame
        A DataFrame with the following columns:
        - 'parcel_id': Identifier for the property (from `tidyparcel`).
        - 'zoning_id': The index of the corresponding row from `tidyzoning`.
        - 'allowed': A boolean value indicating whether the building's lot coverage 
    """
    ureg = UnitRegistry()
    results = []

    # Calculate the floor area of the building
    if len(tidybuilding['footprint']) == 1:
        footprint = tidybuilding['footprint'].iloc[0]
    else:
        return pd.DataFrame(columns=['zoning_id', 'allowed', 'constraint_min_note', 'constraint_max_note']) # Return an empty DataFrame
    
    # Calculate lot_coverage for each parcel_id
    for parcel_id, group in tidyparcel.groupby("parcel_id"):
        parcel_without_centroid = group[(group['side'].notna()) & (group['side'] != "centroid")]
        polygons = list(polygonize(unary_union(parcel_without_centroid.geometry)))
        lot_polygon = unary_union(polygons)
        lot_area = lot_polygon.area * 10.7639  #ft2

        if lot_area == 0:
            continue

        lot_coverage = (footprint / lot_area) * 100
            
        # Iterate through each row in tidyzoning
        for index, zoning_row in tidyzoning.iterrows():
            zoning_req = get_zoning_req(tidybuilding, zoning_row.to_frame().T, tidyparcel)  # ✅ Fix the issue of passing Series

            # Fix the string check here
            if isinstance(zoning_req, str) and zoning_req == "No zoning requirements recorded for this district":
                results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': None, 'constraint_max_note': None})
                continue
            # If zoning_req is empty, consider it allowed
            if zoning_req is None or zoning_req.empty:
                results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': None, 'constraint_max_note': None})
                continue
            # Check if zoning constraints include 'lot_coverage'
            if 'lot_coverage' in zoning_req['spec_type'].values:
                lot_coverage_row = zoning_req[zoning_req['spec_type'] == 'lot_coverage']
                min_lot_coverage = lot_coverage_row['min_value'].values[0]  # Extract min values
                max_lot_coverage = lot_coverage_row['max_value'].values[0]  # Extract max values
                min_select = lot_coverage_row['min_select'].values[0]  # Extract min select info
                max_select = lot_coverage_row['max_select'].values[0]  # Extract max select info
                constraint_min_note = lot_coverage_row['constraint_min_note'].values[0] # Extract min constraint note
                constraint_max_note = lot_coverage_row['constraint_max_note'].values[0] # Extract max constraint note
                
                # If min_select or max_select is 'OZFS Error', default to allowed
                if min_select == 'OZFS Error' or max_select == 'OZFS Error':
                    results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})
                    continue

                # Handle NaN values and list
                # Handle min_lot_coverage
                if not isinstance(min_lot_coverage, list):
                    min_lot_coverage = [0] if min_lot_coverage is None or pd.isna(min_lot_coverage) or isinstance(min_lot_coverage, str) else [min_lot_coverage]
                else:
                    # Filter out NaN and None values, ensuring at least one valid value
                    min_lot_coverage = [v for v in min_lot_coverage if pd.notna(v) and v is not None and not isinstance(v, str)]
                    if not min_lot_coverage:  # If all values are NaN or None, replace with default value
                        min_lot_coverage = [0]
                # Handle max_lot_coverage
                if not isinstance(max_lot_coverage, list):
                    max_lot_coverage = [100] if max_lot_coverage is None or pd.isna(max_lot_coverage) or isinstance(max_lot_coverage, str) else [max_lot_coverage]
                else:
                    # Filter out NaN and None values, ensuring at least one valid value
                    max_lot_coverage = [v for v in max_lot_coverage if pd.notna(v) and v is not None and not isinstance(v, str)]
                    if not max_lot_coverage:  # If all values are NaN or None, replace with default value
                        max_lot_coverage = [100]
                
                # Check min condition
                min_check_1 = min(min_lot_coverage) <= lot_coverage
                min_check_2 = max(min_lot_coverage) <= lot_coverage
                if min_select in ["either", None]:
                    min_allowed = min_check_1 or min_check_2
                elif min_select == "unique":
                    if min_check_1 and min_check_2:
                        min_allowed = True
                    elif not min_check_1 and not min_check_2:
                        min_allowed = False
                    else:
                        min_allowed = "MAYBE"
                
                # Check max condition
                max_check_1 = min(max_lot_coverage) >= lot_coverage
                max_check_2 = max(max_lot_coverage) >= lot_coverage
                if max_select in ["either", None]:
                    max_allowed = max_check_1 or max_check_2
                elif max_select == "unique":
                    if max_check_1 and max_check_2:
                        max_allowed = True
                    elif not max_check_1 and not max_check_2:
                        max_allowed = False
                    else:
                        max_allowed = "MAYBE"
                
                # Determine final allowed status
                if min_allowed == "MAYBE" or max_allowed == "MAYBE":
                    allowed = "MAYBE"
                else:
                    allowed = min_allowed and max_allowed
                
                results.append({'zoning_id': index, 'allowed': allowed, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})
            else:
                results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': None, 'constraint_max_note': None})  # If zoning has no constraints, default to True

    # Return a DataFrame containing the results for all zoning_ids
    return pd.DataFrame(results)