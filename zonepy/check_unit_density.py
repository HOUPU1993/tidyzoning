import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from zonepy import get_zoning_req

def check_unit_density(tidybuilding, tidyzoning, tidyparcel):
    """
    Checks whether the unit_density of a given building complies with zoning constraints.

    Parameters:
    ----------
    tidybuilding : A GeoDataFrame containing information about a single building. 
    tidyzoning : A GeoDataFrame containing zoning constraints. It may have multiple rows,
    tidyparcel : A GeoDataFrame containing parcel geometries, used to calculate the lot area.

    Returns:
    -------
    DataFrame
        A DataFrame with the following columns:
        - 'zoning_id': The index of the corresponding row from `tidyzoning`.
        - 'allowed': A boolean value indicating whether the building's building's unit density is compliant.
        - 'constraint_min_note': The constraint note for the minimum value.
        - 'constraint_max_note': The constraint note for the maximum value.
    
    How to use:
    check_unit_density_result = check_unit_density(tidybuilding_4_fam, tidyzoning, tidyparcel[tidyparcel['parcel_id'] == '10'])
    """
    results = []
    # Check the data from the tidybuilding
    units_0bed = tidybuilding['units_0bed'].sum() if 'units_0bed' in tidybuilding.columns else 0
    units_1bed = tidybuilding['units_1bed'].sum() if 'units_1bed' in tidybuilding.columns else 0
    units_2bed = tidybuilding['units_2bed'].sum() if 'units_2bed' in tidybuilding.columns else 0
    units_3bed = tidybuilding['units_3bed'].sum() if 'units_3bed' in tidybuilding.columns else 0
    units_4bed = tidybuilding['units_4bed'].sum() if 'units_4bed' in tidybuilding.columns else 0
    total_units = units_0bed + units_1bed + units_2bed + units_3bed + units_4bed
    
    # Calculate unit_densityarcel_ID
    lot_area = tidyparcel["lot_area"].iloc[0] if tidyparcel is not None and not tidyparcel.empty else None
    if lot_area is not None and lot_area != 0:
        unit_density = total_units / lot_area #units per acre
    else:
        unit_density = 0  # or maybe 0 or np.nan depending on your context

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
        # Check if zoning constraints include 'unit_density'
        if 'unit_density' in zoning_req['spec_type'].values:
            unit_density_row = zoning_req[zoning_req['spec_type'] == 'unit_density']
            min_unit_density = unit_density_row['min_value'].values[0]  # Extract min values
            max_unit_density = unit_density_row['max_value'].values[0]  # Extract max values
            min_select = unit_density_row['min_select'].values[0]  # Extract min select info
            max_select = unit_density_row['max_select'].values[0]  # Extract max select info
            constraint_min_note = unit_density_row['constraint_min_note'].values[0] # Extract min constraint note
            constraint_max_note = unit_density_row['constraint_max_note'].values[0] # Extract max constraint note
            
            # If min_select or max_select is 'OZFS Error', default to allowed
            if min_select == 'OZFS Error' or max_select == 'OZFS Error':
                results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})
                continue

            # Handle NaN values and list
            # Handle min_unit_density
            if not isinstance(min_unit_density, list):
                min_unit_density = [0] if min_unit_density is None or pd.isna(min_unit_density) or isinstance(min_unit_density, str) else [min_unit_density]
            else:
                # Filter out NaN and None values, ensuring at least one valid value
                min_unit_density = [v for v in min_unit_density if pd.notna(v) and v is not None and not isinstance(v, str)]
                if not min_unit_density:  # If all values are NaN or None, replace with default value
                    min_unit_density = [0]
            # Handle max_unit_density
            if not isinstance(max_unit_density, list):
                max_unit_density = [1000000] if max_unit_density is None or pd.isna(max_unit_density) or isinstance(max_unit_density, str) else [max_unit_density]
            else:
                # Filter out NaN and None values, ensuring at least one valid value
                max_unit_density = [v for v in max_unit_density if pd.notna(v) and v is not None and not isinstance(v, str)]
                if not max_unit_density:  # If all values are NaN or None, replace with default value
                    max_unit_density = [1000000]
            
            # Check min condition
            min_check_1 = min(min_unit_density) <= unit_density
            min_check_2 = max(min_unit_density) <= unit_density
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
            max_check_1 = min(max_unit_density) >= unit_density
            max_check_2 = max(max_unit_density) >= unit_density
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

    return pd.DataFrame(results)