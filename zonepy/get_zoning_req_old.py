import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union, polygonize
import random
from zonepy import find_bldg_type

def get_zoning_req(tidybuilding, tidyzoning, tidyparcel=None):
    """
    Process building, zoning, and parcel information to generate structured Zoning requirement data.
    
    :param tidybuilding: Building data (DataFrame)
    :param tidyzoning: Zoning data (DataFrame)
    :param tidyparcel: Parcel data (GeoDataFrame), optional
    :return: DataFrame containing all calculated results
    :How to use: get_zoning_req_results = get_zoning_req(tidybuilding_4_fam, tidyzoning.loc[[2]], tidyparcel[tidyparcel['parcel_id'] == '10'])
    """
    def zoning_extract(tidybuilding, tidyzoning, tidyparcel=None):
        columns_to_extract = ['structure_constraints', 'other_constraints', 'lot_constraints']
        extracted_data = []
        
        for col in columns_to_extract:
            for index, row in tidyzoning.iterrows():
                constraints = row[col]
                if isinstance(constraints, dict):  
                    for constraint_type, entries in constraints.items():
                        if isinstance(entries, list):  
                            for entry in entries:
                                flattened_entry = {
                                    "original_index": index,
                                    "source_column": col,
                                    "constraint_type": constraint_type,
                                }
                                for key, value in entry.items():  
                                    flattened_entry[key] = value
                                extracted_data.append(flattened_entry)
        district_constraints = pd.DataFrame(extracted_data)

        # If no parcel data is provided
        lot_width = tidyparcel["lot_width"].iloc[0] if tidyparcel is not None and not tidyparcel.empty else None
        lot_depth = tidyparcel["lot_depth"].iloc[0] if tidyparcel is not None and not tidyparcel.empty else None
        lot_area = tidyparcel["lot_area"].iloc[0] if tidyparcel is not None and not tidyparcel.empty else None

        # Check the data from the tidybuilding
        bedrooms = None
        total_bedrooms = tidybuilding.get('total_bedrooms', [None])[0]
        units_0bed = tidybuilding['units_0bed'].sum() if 'units_0bed' in tidybuilding.columns else 0
        units_1bed = tidybuilding['units_1bed'].sum() if 'units_1bed' in tidybuilding.columns else 0
        units_2bed = tidybuilding['units_2bed'].sum() if 'units_2bed' in tidybuilding.columns else 0
        units_3bed = tidybuilding['units_3bed'].sum() if 'units_3bed' in tidybuilding.columns else 0
        units_4bed = tidybuilding['units_4bed'].sum() if 'units_4bed' in tidybuilding.columns else 0
        total_units = tidybuilding.get('total_units', [None])[0]
        fl_area = tidybuilding.get('gross_fl_area', [None])[0]
        height = tidybuilding.get('height', [None])[0]
        height_eave = tidybuilding.get('height_eave', [None])[0]
        floors = tidybuilding.get('stories', [None])[0]
        min_unit_size = tidybuilding.get('min_unit_size', [None])[0]
        max_unit_size = tidybuilding.get('max_unit_size', [None])[0]
        parking_enclosed = tidybuilding.get('parking_enclosed', [None])[0]
        parking_covered = tidybuilding.get('parking_covered', [None])[0]
        parking_uncovered = tidybuilding.get('parking_uncovered', [None])[0]
        parking_floors = tidybuilding.get('parking_floors', [None])[0]
        parking_bel_grade = tidybuilding.get('parking_bel_grade', [None])[0]
        garage_entry = tidybuilding.get('garage_entry', [None])[0]
        units_floor1 = tidybuilding.get('units_floor1', [None])[0]
        units_floor2 = tidybuilding.get('units_floor2', [None])[0]
        units_floor3 = tidybuilding.get('units_floor3', [None])[0]
        bldg_width = tidybuilding.get('width', [None])[0]
        bldg_dpth  = tidybuilding.get('depth', [None])[0]
        far = fl_area / lot_area if lot_area is not None else None

        return {
            # From tidyzoning
            "district_constraints": district_constraints, 
            # From tidyparcel
            "lot_width": lot_width, 
            "lot_depth": lot_depth,
            "lot_area": lot_area,
            # From tidybuilding
            "bedrooms": bedrooms, 
            "total_bedrooms": total_bedrooms,
            "units_0bed": units_0bed,
            "units_1bed": units_1bed,
            "units_2bed": units_2bed,
            "units_3bed": units_3bed,
            "units_4bed": units_4bed,
            "total_units": total_units,
            "fl_area": fl_area,
            "height": height,
            "height_eave": height_eave,
            "floors": floors,
            "min_unit_size": min_unit_size,
            "max_unit_size": max_unit_size,
            "parking_enclosed": parking_enclosed,
            "parking_covered": parking_covered,
            "parking_uncovered": parking_uncovered,
            "parking_floors": parking_floors,
            "parking_bel_grade": parking_bel_grade,
            "garage_entry": garage_entry,
            "units_floor1": units_floor1,
            "units_floor2": units_floor2,
            "units_floor3": units_floor3,
            "bldg_width": bldg_width,
            "bldg_dpth": bldg_dpth,
            # Combined tidy zoning and tidyparcel together
            "far": far   
        }

    def evaluate_conditions_and_expressions(rules, context):
        # If rules is a dict, like {'expression': '30'}
        if isinstance(rules, dict) and "expression" in rules:  
            # If the expression is "NA" or other non-numeric string, return None
            if str(rules["expression"]).strip().upper() == "NA":
                return None, None, None  
            try:
                return eval(str(rules["expression"]), {}, context), None, None
            except Exception:
                return "OZFS Error", None, None
        # If rules is a list, like [{'conditions': ['bedrooms== 0'], 'expression': 500}, {'conditions': ['bedrooms == 1'], 'expression': 700}]
        if not isinstance(rules, list):  
            return None, None, None
        
        all_results = []
        constraint_note = None
        select_value = None
        
        for rule in rules:
            conditions = rule.get("conditions", [])  # List: [{condition_1, expression_1},{condition_2, expression_2}]
            if isinstance(conditions, str):
                conditions = [conditions]
            expression = rule.get("expression", None)  # Single string: {'expression': '30'}
            expressions_list = rule.get("expressions", [])  # List: [{'expression_1': '10'}.{'expression_2': '20'}.select:"min"]
            logical_operator = rule.get("logical_operator", None)  # Single string: [And/Or]
            select = rule.get("select", None)  # List: [min, max, unique, either]
            select_info = rule.get("select_info", None) # specific select information
            
            if select:
                select_value = select
            try:
                '''If logical_operator exists, calculate conditions_met according to AND / OR logic.
                   If conditions exist but logical_operator does not, still calculate conditions_met.
                   If conditions are empty, default conditions_met = True (for expressions_list).'''
                if conditions:
                    if logical_operator == "AND":
                        conditions_met = all(eval(cond, {}, context) for cond in conditions)
                    elif logical_operator == "OR":
                        conditions_met = any(eval(cond, {}, context) for cond in conditions)
                    else:
                        conditions_met = all(eval(cond, {}, context) for cond in conditions)  # No `logical_operator`, default `AND`
                else:
                    conditions_met = True  # If no `conditions`, default to allow execution (for `expressions_list`)

                # Handle single `expression`
                if conditions_met and expression:
                    result = eval(str(expression), {}, context)
                    all_results.append(result)

                # Handle `expressions_list` (can execute even without `conditions`)
                if expressions_list:
                    temp_results = [eval(str(expr), {}, context) for expr in expressions_list]

                    # Handle select logic
                    if select == "max":
                        all_results.append(max(temp_results))
                    elif select == "min":
                        all_results.append(min(temp_results))
                    elif select == "unique":
                        all_results.append(list(set(temp_results)))  # Remove duplicates
                    elif select == "either":
                        all_results.append(list(set(temp_results)))   # Random choice
                    else:
                        all_results.extend(temp_results)  # Default to store all results
                        
                    # If `select_info` has a value, use it; if empty, default to "unique requirements not specified"
                    if select_info:
                        constraint_note = select_info
                    elif constraint_note is None: 
                        constraint_note = "unique requirements not specified"

            except Exception:
                return "OZFS Error", None, None
            
        # Unified return value
        return (all_results[0] if len(all_results) == 1 else all_results) if all_results else "OZFS Error", constraint_note, select_value

    def process_zoning_constraints(result, tidybuilding):
        district_constraints = result["district_constraints"]
        bldg_type = find_bldg_type(tidybuilding)
        results = []
        context = {**result}  # Get all calculated results
        for _, constraint in district_constraints.iterrows():
            if bldg_type not in constraint["use_name"]:
                continue
            min_val_expression = constraint.get("min_val", None)
            max_val_expression = constraint.get("max_val", None)
            constraint_min_val, constraint_min_note, min_select = evaluate_conditions_and_expressions(min_val_expression, context) if min_val_expression else (None, None, None)
            constraint_max_val, constraint_max_note, max_select = evaluate_conditions_and_expressions(max_val_expression, context) if max_val_expression else (None, None, None)

            results.append({
                "constraint_type": constraint.get("source_column", None),
                "spec_type": constraint.get("constraint_type", None),
                "min_value": constraint_min_val,
                "max_value": constraint_max_val,
                "unit": constraint.get("unit", None),
                "constraint_min_note": constraint_min_note if constraint_min_note  else None,
                "constraint_max_note": constraint_max_note if constraint_max_note else None,
                "min_select": min_select if min_select else None,
                "max_select": max_select if max_select else None
            })
        return pd.DataFrame(results)

    result = zoning_extract(tidybuilding, tidyzoning, tidyparcel)
    processed_constraints = process_zoning_constraints(result, tidybuilding)
    if processed_constraints.empty:
        return processed_constraints

    # now it's safe to dropna and squeeze
    processed_constraints = processed_constraints.dropna(
        subset=['min_value','max_value'], how='all'
    ).reset_index(drop=True)

    for col in ['min_value','max_value']:
        # def squeeze(vals):
        #     if isinstance(vals, list) and vals:
        #         return [min(vals), max(vals)]
        #     return vals
        def squeeze(vals):
            if isinstance(vals, list) and vals:
                # flatten any nested lists:
                flat = []
                for v in vals:
                    if isinstance(v, list):
                        flat.extend(v)
                    else:
                        flat.append(v)
                return [min(flat), max(flat)]
            return vals

        processed_constraints[col] = processed_constraints[col].apply(squeeze)
    return processed_constraints