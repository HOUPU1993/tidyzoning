import pandas as pd
import numpy as np
from pint import UnitRegistry
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from tidyzoning import get_zoning_req

def check_unit_qty(tidybuilding, tidyzoning, tidyparcel=None):
    """
    Check if a building's unit quantity and bedroom proportions meet the zoning requirements.

    Parameters:
    -----------
    tidybuilding : GeoDataFrame
        Contains information about a single building. Must include a 'total_units' field (total number of units)
        along with optional fields such as 'units_0bed', 'units_1bed', 'units_2bed', 'units_3bed', and 'units_4bed'.
    tidyzoning : GeoDataFrame
        Contains zoning constraints and may include multiple rows.
    tidyparcel : optional
        Additional parcel data that may further constrain the building location.

    Returns:
    --------
    DataFrame
        A DataFrame with the following columns:
          - 'zoning_id': The index from the corresponding row of tidyzoning.
          - 'allowed': A boolean or string indicating whether the building's unit counts and bedroom proportions comply
                       with the requirements (True, False, or "MAYBE").
          - 'constraint_min_note': The explanatory note for the minimum constraint.
          - 'constraint_max_note': The explanatory note for the maximum constraint.

    Example:
    --------
    result = check_unit_qty(tidybuilding, tidyzoning, tidyparcel[tidyparcel['parcel_id'] == '10'])
    """
    ureg = UnitRegistry()  # Not really needed for these comparisons, but kept for consistency with similar functions.
    results = []

    # Extract basic building data
    total_units = tidybuilding['total_units'].iloc[0]
    
    units_0bed = tidybuilding['units_0bed'].iloc[0] if 'units_0bed' in tidybuilding.columns else 0
    units_1bed = tidybuilding['units_1bed'].iloc[0] if 'units_1bed' in tidybuilding.columns else 0
    units_2bed = tidybuilding['units_2bed'].iloc[0] if 'units_2bed' in tidybuilding.columns else 0
    units_3bed = tidybuilding['units_3bed'].iloc[0] if 'units_3bed' in tidybuilding.columns else 0
    units_4bed = tidybuilding['units_4bed'].iloc[0] if 'units_4bed' in tidybuilding.columns else 0

    pct_0bed = units_0bed / total_units
    pct_1bed = units_1bed / total_units
    pct_2bed = units_2bed / total_units
    pct_3bed = units_3bed / total_units
    pct_4bed = units_4bed / total_units

    # Construct a dictionary of building values for checking
    building_values = {
        'unit_qty': total_units,
        'pct_units_0bed': pct_0bed,
        'pct_units_1bed': pct_1bed,
        'pct_units_2bed': pct_2bed,
        'pct_units_3bed': pct_3bed,
        'pct_units_4bed': pct_4bed,
    }
    
    # Iterate over each zoning row
    for index, zoning_row in tidyzoning.iterrows():
        zoning_req = get_zoning_req(tidybuilding, zoning_row.to_frame().T, tidyparcel)

        # If there are no zoning requirements, or a specific note is returned, default to allowed
        if isinstance(zoning_req, str) and zoning_req == "No zoning requirements recorded for this district":
            results.append({
                'zoning_id': index,
                'allowed': True,
                'constraint_min_note': None,
                'constraint_max_note': None
            })
            continue
        if zoning_req is None or zoning_req.empty:
            results.append({
                'zoning_id': index,
                'allowed': True,
                'constraint_min_note': None,
                'constraint_max_note': None
            })
            continue

        # Initialize overall status and lists for collecting constraint notes
        any_false = False
        any_maybe = False
        collected_min_notes = []
        collected_max_notes = []

        # Check each field in building_values against the corresponding zoning requirements
        for spec_key, building_val in building_values.items():
            if spec_key in zoning_req['spec_type'].values:
                # Extract constraint parameters for the current specification
                row = zoning_req[zoning_req['spec_type'] == spec_key]
                min_val = row['min_value'].values[0]
                max_val = row['max_value'].values[0]
                min_select = row['min_select'].values[0]
                max_select = row['max_select'].values[0]
                note_min = row['constraint_min_note'].values[0]
                note_max = row['constraint_max_note'].values[0]

                # Process the minimum value: ensure it is a list of valid values, defaulting to 0 if needed
                if not isinstance(min_val, list):
                    min_val = [0] if min_val is None or pd.isna(min_val) or isinstance(min_val, str) else [min_val]
                else:
                    min_val = [v for v in min_val if pd.notna(v) and v is not None and not isinstance(v, str)]
                    if not min_val:
                        min_val = [0]
                
                # Process the maximum value: ensure it is a list of valid values, defaulting to a large number if needed
                if not isinstance(max_val, list):
                    max_val = [1000000] if max_val is None or pd.isna(max_val) or isinstance(max_val, str) else [max_val]
                else:
                    max_val = [v for v in max_val if pd.notna(v) and v is not None and not isinstance(v, str)]
                    if not max_val:
                        max_val = [1000000]
                
                # For quantities and proportions, no unit conversion is needed; directly compare the values.
                min_check_1 = min(min_val) <= building_val
                min_check_2 = max(min_val) <= building_val
                if min_select in ["either", None]:
                    min_allowed = min_check_1 or min_check_2
                elif min_select == "unique":
                    if min_check_1 and min_check_2:
                        min_allowed = True
                    elif not min_check_1 and not min_check_2:
                        min_allowed = False
                    else:
                        min_allowed = "MAYBE"
                else:
                    min_allowed = min_check_1 or min_check_2
                
                max_check_1 = min(max_val) >= building_val
                max_check_2 = max(max_val) >= building_val
                if max_select in ["either", None]:
                    max_allowed = max_check_1 or max_check_2
                elif max_select == "unique":
                    if max_check_1 and max_check_2:
                        max_allowed = True
                    elif not max_check_1 and not max_check_2:
                        max_allowed = False
                    else:
                        max_allowed = "MAYBE"
                else:
                    max_allowed = max_check_1 or max_check_2

                # Combine the minimum and maximum checks for the current field
                if min_allowed == "MAYBE" or max_allowed == "MAYBE":
                    current_allowed = "MAYBE"
                else:
                    current_allowed = min_allowed and max_allowed

                # Record the result and the associated notes for this field
                if current_allowed == False:
                    any_false = True
                    collected_min_notes.append(note_min)
                    collected_max_notes.append(note_max)
                elif current_allowed == "MAYBE":
                    # The 'if not any_false:' here means that we only record "MAYBE" if no field
                    # has already been marked as False. If any_false is True, the overall result will be False.
                    if not any_false:
                        any_maybe = True
                        collected_min_notes.append(note_min)
                        collected_max_notes.append(note_max)

        # Determine the overall allowed status based on the individual field results
        if any_false:
            overall_allowed = False
        elif any_maybe:
            overall_allowed = "MAYBE"
        else:
            overall_allowed = True

        results.append({
            'zoning_id': index, 
            'allowed': overall_allowed,
            'constraint_min_note': ', '.join([str(x) for x in collected_min_notes]) if collected_min_notes else None,
            'constraint_max_note': ', '.join([str(x) for x in collected_max_notes]) if collected_max_notes else None
        })

    return pd.DataFrame(results)