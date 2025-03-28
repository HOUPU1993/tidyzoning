import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.ops import unary_union, polygonize
from tidyzoning import get_zoning_req
from tidyzoning import find_bldg_type
import re

'''Part I: Only check unit size avg'''
# Check the Unit_size_avg constraints
def check_unit_size_avg_fun(tidybuilding, tidyzoning, tidyparcel=None):
    """
    Checks whether the Floor Area Ratio (FAR) of a given building complies with zoning constraints.

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
        - 'allowed': A boolean value indicating whether the building's FAR 
        - 'constraint_min_note': The constraint note for the minimum value.
        - 'constraint_max_note': The constraint note for the maximum value.
        
    How to use:
    check_unit_size_result = check_unit_size(tidybuilding_4_fam, tidyzoning, tidyparcel[tidyparcel['parcel_id'] == '10'])
    """

    results = []

    # Calculate the floor area of the building
    if len(tidybuilding['mean_unit_size']) == 1:
        mean_unit_size = tidybuilding['mean_unit_size'].iloc[0]
    else:
        return pd.DataFrame(columns=['zoning_id', 'allowed', 'constraint_min_note', 'constraint_max_note']) # Return an empty DataFrame
    
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
        # Check if zoning constraints include 'unit_size_avg'
        if 'unit_size_avg' in zoning_req['spec_type'].values:
            unit_size_avg_row = zoning_req[zoning_req['spec_type'] == 'unit_size_avg']
            min_unit_size = unit_size_avg_row['min_value'].values[0]  # Extract min values
            max_unit_size = unit_size_avg_row['max_value'].values[0]  # Extract max values
            min_select = unit_size_avg_row['min_select'].values[0]  # Extract min select info
            max_select = unit_size_avg_row['max_select'].values[0]  # Extract max select info
            constraint_min_note = unit_size_avg_row['constraint_min_note'].values[0] # Extract min constraint note
            constraint_max_note = unit_size_avg_row['constraint_max_note'].values[0] # Extract max constraint note
            
            # If min_select or max_select is 'OZFS Error', default to allowed
            if min_select == 'OZFS Error' or max_select == 'OZFS Error':
                results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})
                continue

            # Handle NaN values and list
            # Handle min_unit_size
            if not isinstance(min_unit_size, list):
                min_unit_size = [0] if min_unit_size is None or pd.isna(min_unit_size) or isinstance(min_unit_size, str) else [min_unit_size]
            else:
                # Filter out NaN and None values, ensuring at least one valid value
                min_unit_size = [v for v in min_unit_size if pd.notna(v) and v is not None and not isinstance(v, str)]
                if not min_unit_size:  # If all values are NaN or None, replace with default value
                    min_unit_size = [0]
            # Handle max_unit_size
            if not isinstance(max_unit_size, list):
                max_unit_size = [1000000] if max_unit_size is None or pd.isna(max_unit_size) or isinstance(max_unit_size, str) else [max_unit_size]
            else:
                # Filter out NaN and None values, ensuring at least one valid value
                max_unit_size = [v for v in max_unit_size if pd.notna(v) and v is not None and not isinstance(v, str)]
                if not max_unit_size:  # If all values are NaN or None, replace with default value
                    max_unit_size = [1000000]
            
            # Check min condition
            min_check_1 = min(min_unit_size) <= mean_unit_size
            min_check_2 = max(min_unit_size) <= mean_unit_size
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
            max_check_1 = min(max_unit_size) >= mean_unit_size
            max_check_2 = max(max_unit_size) >= mean_unit_size
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


'''Part II: Only check unit size'''
# Check the Unit_size constraints
def check_unit_size_fun(tidybuilding, tidyzoning, tidyparcel=None):
    """
    Extract tidybuilding data and check zoning constraints, return whether it meets the requirements
    """
    results = []
    bldg_type = find_bldg_type(tidybuilding)

    # Calculate parcel information
    lot_width, lot_depth, lot_area = None, None, None
    if tidyparcel is not None:
        parcel_results = []
        for parcel_id, group in tidyparcel.groupby('parcel_id'):
            front_of_parcel = group[group['side'] == "front"]
            side_of_parcel = group[group['side'] == "Interior side"]
            parcel_without_centroid = group[(group['side'].notna()) & (group['side'] != "centroid")]

            lot_width = front_of_parcel.geometry.length.sum() * 3.28084
            lot_depth = side_of_parcel.geometry.length.sum() * 3.28084
            polygons = polygonize(unary_union(parcel_without_centroid.geometry))
            lot_polygon = unary_union(list(polygons))
            lot_area = lot_polygon.area * 10.7639
            parcel_results.append({
                "parcel_id": parcel_id,
                "lot_width": lot_width,
                "lot_depth": lot_depth,
                "lot_area": lot_area
            })

        parcel_results = pd.DataFrame(parcel_results)
        lot_width = parcel_results["lot_width"].iloc[0] if not parcel_results.empty else None
        lot_depth = parcel_results["lot_depth"].iloc[0] if not parcel_results.empty else None
        lot_area = parcel_results["lot_area"].iloc[0] if not parcel_results.empty else None

    # Build context
    context = {
        "total_bedrooms": tidybuilding.get('total_bedrooms', [None])[0],
        "units_0bed": tidybuilding['units_0bed'].sum() if 'units_0bed' in tidybuilding.columns else 0,
        "units_1bed": tidybuilding['units_1bed'].sum() if 'units_1bed' in tidybuilding.columns else 0,
        "units_2bed": tidybuilding['units_2bed'].sum() if 'units_2bed' in tidybuilding.columns else 0,
        "units_3bed": tidybuilding['units_3bed'].sum() if 'units_3bed' in tidybuilding.columns else 0,
        "units_4bed": tidybuilding['units_4bed'].sum() if 'units_4bed' in tidybuilding.columns else 0,
        "total_units": tidybuilding.get('total_units', [None])[0],
        "gross_fl_area": tidybuilding.get('gross_fl_area', [None])[0],
        "height": tidybuilding.get('height', [None])[0],
        "height_eave": tidybuilding.get('height_eave', [None])[0],
        "stories": tidybuilding.get('stories', [None])[0],
        "min_unit_size": tidybuilding.get('min_unit_size', [None])[0],
        "max_unit_size": tidybuilding.get('max_unit_size', [None])[0],
        "parking_enclosed": tidybuilding.get('parking_enclosed', [None])[0],
        "parking_covered": tidybuilding.get('parking_covered', [None])[0],
        "parking_uncovered": tidybuilding.get('parking_uncovered', [None])[0],
        "parking_floors": tidybuilding.get('parking_floors', [None])[0],
        "parking_bel_grade": tidybuilding.get('parking_bel_grade', [None])[0],
        "garage_entry": tidybuilding.get('garage_entry', [None])[0],
        "units_floor1": tidybuilding.get('units_floor1', [None])[0],
        "units_floor2": tidybuilding.get('units_floor2', [None])[0],
        "units_floor3": tidybuilding.get('units_floor3', [None])[0],
        "width": tidybuilding.get('width', [None])[0],
        "depth": tidybuilding.get('depth', [None])[0],
        "lot_width": lot_width,
        "lot_depth": lot_depth,
        "lot_area": lot_area,
        "far": tidybuilding.get('gross_fl_area', [None])[0] / lot_area if lot_area is not None else None,
    }

    # Extract units_xbed_minsize and units_xbed_maxsize from tidybuilding
    min_size_dict = {int(re.search(r"units_(\d+)bed_minsize", col).group(1)): float(tidybuilding[col].iloc[0])
                     for col in tidybuilding.columns if re.search(r"units_\d+bed_minsize", col)}
    
    max_size_dict = {int(re.search(r"units_(\d+)bed_maxsize", col).group(1)): float(tidybuilding[col].iloc[0])
                     for col in tidybuilding.columns if re.search(r"units_\d+bed_maxsize", col)}

    if not min_size_dict or not max_size_dict:
        return pd.DataFrame(columns=['zoning_id', 'allowed', 'constraint_min_note', 'constraint_max_note'])

    # Iterate through tidyzoning
    for index, zoning_row in tidyzoning.iterrows():
        dist_info_constraints = zoning_row['dist_info']
        if not isinstance(dist_info_constraints, dict):
            dist_info_constraints = {}

        uses_permitted = dist_info_constraints.get('uses_permitted', {}).get('uses_value', [])
        if isinstance(uses_permitted, str):
            uses_permitted = [uses_permitted]
        if bldg_type not in uses_permitted:
            results.append({'zoning_id': index, 'allowed': True})
            continue 

        # Get `structure_constraints`
        structure_constraints = zoning_row['structure_constraints']
        if not isinstance(structure_constraints, dict):
            structure_constraints = {}

        unit_size_constraints = structure_constraints.get('unit_size', [])
        if not unit_size_constraints:
            results.append({'zoning_id': index, 'allowed': True})
            continue

        found_bldg_type = any(bldg_type in constraint.get('use_name', []) for constraint in unit_size_constraints)
        if not found_bldg_type:
            results.append({'zoning_id': index, 'allowed': True})
            continue

        allowed = True
        constraint_min_note = None
        constraint_max_note = None

        def evaluate_constraints(size_dict, rules, comparison_func):
            """
            Handle min_val and max_val constraints.

            :param size_dict: min_size_dict or max_size_dict
            :param rules: min_val_rules or max_val_rules
            :param comparison_func: lambda expression for comparing unit sizes
            :return: (allowed status (True / False / "MAYBE"), constraint information select_info)
            """
            constraint_values = {}
            select_info = None

            def evaluate_expression(expression, context):
                """ Evaluate mathematical expression, e.g., '950 + 150 * (bedrooms - 2)' """
                try:
                    return eval(str(expression), {}, context)
                except Exception:
                    return None

            if isinstance(rules, list):
                for num_bedrooms, size in size_dict.items():
                    size = float(size)
                    for rule in rules:
                        conditions = rule.get("conditions", [])
                        expression = rule.get("expression", None)
                        expressions = rule.get("expressions", None)
                        rule_select_info = rule.get("select_info", None)

                        if not expressions and not expression:
                            continue
                        context["bedrooms"] = num_bedrooms
                        if expressions:
                            evaluated_values = [evaluate_expression(expr, context) for expr in expressions]
                        # Handle single expression
                        elif expression:
                            evaluated_values = [evaluate_expression(expression, context)]
                        else:
                            evaluated_values = []
                        evaluated_values = [val for val in evaluated_values if val is not None]
                        try:
                            if any(eval(cond, {}, context) for cond in conditions) or not conditions:
                                constraint_values[num_bedrooms] = evaluated_values
                                if rule_select_info:
                                    select_info = rule_select_info
                        except Exception:
                            continue

            elif isinstance(rules, dict):
                for num_bedrooms, size in size_dict.items():
                    size = float(size)
                    context["bedrooms"] = num_bedrooms  
                    expressions = rules.get("expressions", [])
                    expression = rules.get("expression", None)
                    if not expressions and not expression:
                        continue
                    evaluated_values = []
                    if expressions:
                        evaluated_values = [evaluate_expression(expr, context) for expr in expressions]  
                    elif expression:
                        evaluated_values = [evaluate_expression(expression, context)]  
                    evaluated_values = [val for val in evaluated_values if val is not None]
                    if evaluated_values:
                        constraint_values[num_bedrooms] = evaluated_values
                        
            if not constraint_values:
                return True, select_info

            allowed_list = []
            for num_bedrooms, values in constraint_values.items():
                if num_bedrooms in size_dict:
                    building_size = size_dict[num_bedrooms]
                    checks = [comparison_func(building_size, v) for v in values]

                    if "either" in rules:
                        allowed_list.append(any(checks))
                    elif "unique" in rules:
                        if all(checks):
                            allowed_list.append(True)
                        elif not any(checks):
                            allowed_list.append(False)
                        else:
                            allowed_list.append("MAYBE")
                    else:
                        allowed_list.append(all(checks))

            if "MAYBE" in allowed_list:
                return "MAYBE", select_info
            return all(allowed_list), select_info

        # Check min_val constraints
        min_val_rules = next((c.get("min_val") for c in unit_size_constraints if bldg_type in c.get("use_name", [])), [])
        max_val_rules = next((c.get("max_val") for c in unit_size_constraints if bldg_type in c.get("use_name", [])), [])

        if isinstance(min_val_rules, dict):
            min_val_rules = [min_val_rules]
        if isinstance(max_val_rules, dict):
            max_val_rules = [max_val_rules]

        min_allowed, min_select_info = evaluate_constraints(min_size_dict, min_val_rules, lambda x, y: x >= y)
        max_allowed, max_select_info = evaluate_constraints(max_size_dict, max_val_rules, lambda x, y: x <= y)

        if min_allowed == "MAYBE" or max_allowed == "MAYBE":
            allowed = "MAYBE"
        else:
            allowed = min_allowed and max_allowed

        if min_select_info:
            constraint_min_note = min_select_info
        if max_select_info:
            constraint_max_note = max_select_info

        results.append({'zoning_id': index, 'allowed': allowed, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})

    return pd.DataFrame(results)

'''Part III: CHeck Both'''
# Check the unit size 
def check_unit_size(tidybuilding, tidyzoning, tidyparcel=None):
    """
    Run `check_unit_size_avg` and `check_unit_size`, merge the results, and return the final `allowed` status and constraint information.

    Parameters:
        tidybuilding (GeoDataFrame): Dataset containing building information
        tidyzoning (GeoDataFrame): Dataset containing zoning constraints
        tidyparcel (GeoDataFrame): Dataset containing parcel information

    Returns:
        DataFrame: Final result containing `zoning_id`, `allowed`, `constraint_min_note`, and `constraint_max_note`
    """
    
    # Step 1: Run check_unit_size_avg
    check_unit_size_avg_result = check_unit_size_avg_fun(tidybuilding, tidyzoning, tidyparcel)

    # Step 2: Get `zoning_id` where `allowed` is True or MAYBE
    valid_zoning_ids = check_unit_size_avg_result[
        check_unit_size_avg_result['allowed'].isin([True, "MAYBE"])
    ]['zoning_id']

    # Step 3: Filter tidyzoning (but ensure all zoning_id are retained)
    filtered_tidyzoning = tidyzoning.loc[valid_zoning_ids]

    # Step 4: Run check_unit_size
    check_unit_size_result = check_unit_size_fun(tidybuilding, filtered_tidyzoning, tidyparcel)

    # Step 5: Merge the two results, ensuring all zoning_id are recorded
    merged_result = pd.merge(
        check_unit_size_avg_result, 
        check_unit_size_result, 
        on="zoning_id", 
        how="outer", 
        suffixes=("_avg", "_unit")
    )

    # Step 6: Calculate the final `allowed` status
    def combine_allowed(row):
        avg_allowed = row["allowed_avg"]
        unit_allowed = row["allowed_unit"]

        if avg_allowed is False or unit_allowed is False:
            return False
        elif avg_allowed == "MAYBE" or unit_allowed == "MAYBE":
            return "MAYBE"
        else:
            return True

    merged_result["allowed"] = merged_result.apply(combine_allowed, axis=1)

    # Step 7: Handle `constraint_min_note` and `constraint_max_note`
    def combine_notes(note_avg, note_unit):
        """
        Combine constraint notes:
        - If both are empty, return None
        - If one is empty, return the non-empty value
        - If both are different, combine them with " | " as a separator
        """
        if pd.isna(note_avg) and pd.isna(note_unit):
            return None
        elif pd.isna(note_avg):
            return note_unit
        elif pd.isna(note_unit):
            return note_avg
        else:
            return f"{note_avg} | {note_unit}"

    merged_result["constraint_min_note"] = merged_result.apply(
        lambda row: combine_notes(row["constraint_min_note_avg"], row["constraint_min_note_unit"]),
        axis=1
    )

    merged_result["constraint_max_note"] = merged_result.apply(
        lambda row: combine_notes(row["constraint_max_note_avg"], row["constraint_max_note_unit"]),
        axis=1
    )

    # Step 8: Keep only the final required columns
    final_result = merged_result[[
        "zoning_id", "allowed", "constraint_min_note", "constraint_max_note"
    ]]

    return final_result