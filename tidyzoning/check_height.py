import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from tidyzoning import get_zoning_req

# def check_height(tidybuilding, tidyzoning, tidyparcel=None):
#     """
#     Checks whether the building height of a given building complies with zoning constraints.

#     Parameters:
#     ----------
#     tidybuilding : A GeoDataFrame containing information about a single building. 
#     tidyzoning : A GeoDataFrame containing zoning constraints. It may have multiple rows,
#     tidyparcel : Optional
    
#     Returns:
#     -------
#     DataFrame
#         A DataFrame with the following columns:
#         - 'zoning_id': The index of the corresponding row from `tidyzoning`.
#         - 'allowed': A boolean value indicating whether the building's Height
#         - 'constraint_min_note': The constraint note for the minimum value.
#         - 'constraint_max_note': The constraint note for the maximum value.
        
#     How to use:
#     check_height_result = check_height(tidybuilding_4_fam, tidyzoning, tidyparcel[tidyparcel['parcel_id'] == '10'])
#     """
#     ureg = UnitRegistry()
#     results = []

#     # Calculate the floor area of the building
#     if len(tidybuilding['height']) == 1:
#         height = tidybuilding['height'].iloc[0]
#     else:
#         return pd.DataFrame(columns=['zoning_id', 'allowed', 'constraint_min_note', 'constraint_max_note']) # Return an empty DataFrame
    
#     # Iterate through each row in tidyzoning
#     for index, zoning_row in tidyzoning.iterrows():
#         zoning_req = get_zoning_req(tidybuilding, zoning_row.to_frame().T, tidyparcel)  # ✅ Fix the issue of passing Series

#         # Fix the string check here
#         if isinstance(zoning_req, str) and zoning_req == "No zoning requirements recorded for this district":
#             results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': None, 'constraint_max_note': None})
#             continue
#         # If zoning_req is empty, consider it allowed
#         if zoning_req is None or zoning_req.empty:
#             results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': None, 'constraint_max_note': None})
#             continue
#         # Check if zoning constraints include 'height'
#         if 'height' in zoning_req['spec_type'].values:
#             height_row = zoning_req[zoning_req['spec_type'] == 'height']
#             min_height = height_row['min_value'].values[0]  # Extract min values
#             max_height = height_row['max_value'].values[0]  # Extract max values
#             min_select = height_row['min_select'].values[0]  # Extract min select info
#             max_select = height_row['max_select'].values[0]  # Extract max select info
#             constraint_min_note = height_row['constraint_min_note'].values[0] # Extract min constraint note
#             constraint_max_note = height_row['constraint_max_note'].values[0] # Extract max constraint note
            
#             # If min_select or max_select is 'OZFS Error', default to allowed
#             if min_select == 'OZFS Error' or max_select == 'OZFS Error':
#                 results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})
#                 continue

#             # Handle NaN values and list
#             # Handle min_height
#             if not isinstance(min_height, list):
#                 min_height = [0] if min_height is None or pd.isna(min_height) or isinstance(min_height, str) else [min_height]
#             else:
#                 # Filter out NaN and None values, ensuring at least one valid value
#                 min_height = [v for v in min_height if pd.notna(v) and v is not None and not isinstance(v, str)]
#                 if not min_height:  # If all values are NaN or None, replace with default value
#                     min_height = [0]
#             # Handle max_height
#             if not isinstance(max_height, list):
#                 max_height = [1000000] if max_height is None or pd.isna(max_height) or isinstance(max_height, str) else [max_height]
#             else:
#                 # Filter out NaN and None values, ensuring at least one valid value
#                 max_height = [v for v in max_height if pd.notna(v) and v is not None and not isinstance(v, str)]
#                 if not max_height:  # If all values are NaN or None, replace with default value
#                     max_height = [1000000]

#             # Get the unit and convert
#             unit_column = height_row['unit'].values[0]  # Extract the unit of the specific row
#             # Define the unit mapping
#             unit_mapping = {
#                 "feet": ureg('ft'),
#                 "meters": ureg('m'),
#             }
#             target_unit = unit_mapping.get(unit_column, ureg('ft'))  # Convert the unit of the specific row to a unit recognized by pint, default is ft^2 if no unit
#             # Ensure min/max_height has the correct unit 'ft^2'
#             min_height = [ureg.Quantity(v, target_unit).to('ft').magnitude for v in min_height]
#             max_height = [ureg.Quantity(v, target_unit).to('ft').magnitude for v in max_height]

#             # Check min condition
#             min_check_1 = min(min_height) <= height
#             min_check_2 = max(min_height) <= height
#             if min_select in ["either", None]:
#                 min_allowed = min_check_1 or min_check_2
#             elif min_select == "unique":
#                 if min_check_1 and min_check_2:
#                     min_allowed = True
#                 elif not min_check_1 and not min_check_2:
#                     min_allowed = False
#                 else:
#                     min_allowed = "MAYBE"
            
#             # Check max condition
#             max_check_1 = min(max_height) >= height
#             max_check_2 = max(max_height) >= height
#             if max_select in ["either", None]:
#                 max_allowed = max_check_1 or max_check_2
#             elif max_select == "unique":
#                 if max_check_1 and max_check_2:
#                     max_allowed = True
#                 elif not max_check_1 and not max_check_2:
#                     max_allowed = False
#                 else:
#                     max_allowed = "MAYBE"
            
#             # Determine final allowed status
#             if min_allowed == "MAYBE" or max_allowed == "MAYBE":
#                 allowed = "MAYBE"
#             else:
#                 allowed = min_allowed and max_allowed
            
#             results.append({'zoning_id': index, 'allowed': allowed, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})
#         else:
#             results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': None, 'constraint_max_note': None})  # If zoning has no constraints, default to True

#     return pd.DataFrame(results)

ureg = UnitRegistry()
UNIT_MAP = {
    "feet":   ureg("ft"),
    "meters": ureg("m"),
}

def check_height(tidybuilding, tidyzoning=None, tidyparcel=None, zoning_req=None):
    """
    Fast height check using pre-cached zoning_req, vectorized min/max, and
    module-level UnitRegistry + unit mapping.
    """
    # 1) pull or compute the tiny zoning_req DataFrame
    if zoning_req is None:
        zoning_req = get_zoning_req(tidybuilding, tidyzoning, tidyparcel)

    # 2) extract only the 'height' row (no full DataFrame loop)
    hr = zoning_req[zoning_req.spec_type == "height"]
    if hr.empty:
        # no height constraint ⇒ always allowed
        return pd.DataFrame([{
            "zoning_id":              None,
            "allowed":                True,
            "constraint_min_note":    None,
            "constraint_max_note":    None
        }])

    # assume exactly one row for height
    row = hr.iloc[0]
    min_vals = row.min_value or []
    max_vals = row.max_value or []

    # 3) flatten any nested lists and filter to numeric
    def _clean(vals, default):
        flat = []
        for v in (vals if isinstance(vals, list) else [vals]):
            if isinstance(v, list):
                flat.extend(v)
            elif pd.notna(v) and not isinstance(v, str):
                flat.append(v)
        return np.array(flat or [default], float)

    min_arr = _clean(min_vals, 0.0)
    max_arr = _clean(max_vals, 1e6)

    # 4) convert units just once
    unit = UNIT_MAP.get(row.unit, ureg("ft"))
    min_ft = (min_arr * unit).to("ft").magnitude
    max_ft = (max_arr * unit).to("ft").magnitude

    # 5) grab building height
    if tidybuilding.height.size != 1:
        return pd.DataFrame(columns=["zoning_id","allowed","constraint_min_note","constraint_max_note"])
    h = float(tidybuilding.height.iloc[0])

    # 6) vectorized min/max checks
    #   – for "either"/None, allow if h ≥ any(min_ft) AND h ≤ any(max_ft)
    #   – for "unique", allow only if h ≥ all(min_ft) AND h ≤ all(max_ft)
    sel_min = row.min_select or "either"
    sel_max = row.max_select or "either"

    if sel_min == "unique":
        min_ok = (min_ft.max() <= h) and (min_ft.min() <= h)
    else:
        min_ok = (min_ft.min() <= h) or (min_ft.max() <= h)

    if sel_max == "unique":
        max_ok = (max_ft.min() >= h) and (max_ft.max() >= h)
    else:
        max_ok = (max_ft.min() >= h) or (max_ft.max() >= h)

    # final allowed
    if sel_min == "OZFS Error" or sel_max == "OZFS Error":
        allowed = True
    elif not min_ok or not max_ok:
        allowed = "MAYBE" if (not min_ok or not max_ok) else True
    else:
        allowed = True

    return pd.DataFrame([{
        "zoning_id":           row.original_index,
        "allowed":             allowed,
        "constraint_min_note": row.constraint_min_note,
        "constraint_max_note": row.constraint_max_note
    }])