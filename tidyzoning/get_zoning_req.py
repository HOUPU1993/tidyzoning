import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union, polygonize
import random
from tidyzoning import find_bldg_type

def get_zoning_req(tidybuilding, tidyzoning, tidyparcel=None):
    """
    Process building, zoning, and parcel information to generate structured Zoning requirement data.
    
    :param tidybuilding: Building data (DataFrame)
    :param tidyzoning: Zoning data (DataFrame)
    :param tidyparcel: Parcel data (GeoDataFrame), optional
    :return: DataFrame containing all calculated results
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
        lot_width, lot_depth, lot_area = None, None, None
        if tidyparcel is not None:
            results = []
            for parcel_id, group in tidyparcel.groupby('parcel_id'):
                front_of_parcel = group[group['side'] == "front"]
                side_of_parcel = group[group['side'] == "Interior side"]
                parcel_without_centroid = group[(group['side'].notna()) & (group['side'] != "centroid")]

                lot_width = front_of_parcel.geometry.length.sum() * 3.28084
                lot_depth = side_of_parcel.geometry.length.sum() * 3.28084
                polygons = polygonize(unary_union(parcel_without_centroid.geometry))
                lot_polygon = unary_union(polygons)
                lot_area = lot_polygon.area * 10.7639
                results.append({"parcel_id": parcel_id, "lot_width": lot_width, "lot_depth": lot_depth, "lot_area": lot_area})

            parcel_results = pd.DataFrame(results)
            lot_width = parcel_results["lot_width"].iloc[0] if not parcel_results.empty else None
            lot_depth = parcel_results["lot_depth"].iloc[0] if not parcel_results.empty else None
            lot_area = parcel_results["lot_area"].iloc[0] if not parcel_results.empty else None

        # Check the data from the tidybuilding
        bed_list = {
            'units_0bed': 0,
            'units_1bed': 1,
            'units_2bed': 2,
            'units_3bed': 3,
            'units_4bed': 4
        }
        bedrooms = max([bed_list.get(col, 0) for col in tidybuilding.columns if col in bed_list.keys()])
        units_0bed = tidybuilding['units_0bed'].sum() if 'units_0bed' in tidybuilding.columns else 0
        units_1bed = tidybuilding['units_1bed'].sum() if 'units_1bed' in tidybuilding.columns else 0
        units_2bed = tidybuilding['units_2bed'].sum() if 'units_2bed' in tidybuilding.columns else 0
        units_3bed = tidybuilding['units_3bed'].sum() if 'units_3bed' in tidybuilding.columns else 0
        units_4bed = tidybuilding['units_4bed'].sum() if 'units_4bed' in tidybuilding.columns else 0
        total_units = units_0bed + units_1bed + units_2bed + units_3bed + units_4bed
        fl_area = tidybuilding.get('fl_area', [None])[0]
        fl_area_top = tidybuilding.get('fl_area_top', [None])[0]
        fl_area_bottom = tidybuilding.get('fl_area_bottom', [None])[0]
        height = tidybuilding.get('height', [None])[0]
        height_eave = tidybuilding.get('height_eave', [None])[0]
        floors = tidybuilding.get('stories', [None])[0]
        min_unit_size = tidybuilding.get('min_unit_size', [None])[0]
        max_unit_size = tidybuilding.get('max_unit_size', [None])[0]
        parking_enclosed = tidybuilding.get('parking_enclosed', [None])[0]
        parking_covered = tidybuilding.get('parking_covered', [None])[0]
        parking_uncovered = tidybuilding.get('parking_uncovered', [None])[0]
        parking_floors = tidybuilding.get('parking_floors', [None])[0]
        garage_entry = tidybuilding.get('garage_entry', [None])[0]
        units_floor1 = tidybuilding.get('units_floor1', [None])[0]
        units_floor2 = tidybuilding.get('units_floor2', [None])[0]
        units_floor3 = tidybuilding.get('units_floor3', [None])[0]
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
            "units_0bed": units_0bed,
            "units_1bed": units_1bed,
            "units_2bed": units_2bed,
            "units_3bed": units_3bed,
            "units_4bed": units_4bed,
            "total_units": total_units,
            "fl_area": fl_area,
            "fl_area_top": fl_area_top,
            "fl_area_bottom": fl_area_bottom,
            "height": height,
            "height_eave": height_eave,
            "floors": floors,
            "min_unit_size": min_unit_size,
            "max_unit_size": max_unit_size,
            "parking_enclosed": parking_enclosed,
            "parking_covered": parking_covered,
            "parking_uncovered": parking_uncovered,
            "parking_floors": parking_floors,
            "garage_entry": garage_entry,
            "units_floor1": units_floor1,
            "units_floor2": units_floor2,
            "units_floor3": units_floor3,
            # Combined tidy zoning and tidyparcel together
            "far": far   
        }

    def evaluate_conditions_and_expressions(rules, context):
        # If rules is a dict, like {'expression': '30'}
        if isinstance(rules, dict) and "expression" in rules:  
            try:
                return eval(str(rules["expression"]), {}, context)
            except Exception as e:
                return None
        # If rules is a list, like [{'conditions': ['bedrooms== 0'], 'expression': 500}, {'conditions': ['bedrooms == 1'], 'expression': 700}]
        if not isinstance(rules, list):  
            return None
        all_results = []
        for rule in rules:
            conditions = rule.get("conditions", [])  # List: [{condition_1, expression_1},{condition_2, expression_2}]
            expression = rule.get("expression", None)  # Single string: {'expression': '30'}
            expressions_list = rule.get("expressions", [])  # List: [{'expression_1': '10'}.{'expression_2': '20'}.select:"min"]
            logical_operator = rule.get("logical_operator", None)  # Single string: [And/Or]
            select = rule.get("select", None)  # List: [min, max, unique, either]
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
                        all_results.append(random.choice(temp_results))  # Random choice
                    else:
                        all_results.extend(temp_results)  # Default to store all results
            except Exception as e:
                continue
        # Unified return value
        return all_results[0] if len(all_results) == 1 else (all_results if all_results else None)

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
            constraint_min_val = evaluate_conditions_and_expressions(min_val_expression, context) if min_val_expression else None
            constraint_max_val = evaluate_conditions_and_expressions(max_val_expression, context) if min_val_expression else None
            results.append({
                "constraint_type": constraint.get("source_column", None),
                "spec_type": constraint.get("constraint_type", None),
                "min_value": constraint_min_val,
                "max_value": constraint_max_val,
                "unit": constraint.get("unit", None)
            })
        return pd.DataFrame(results)

    result = zoning_extract(tidybuilding, tidyzoning, tidyparcel)
    processed_constraints = process_zoning_constraints(result, tidybuilding)
    if not processed_constraints.empty:
        processed_constraints = processed_constraints.dropna(subset=['min_value', 'max_value'], how='all').reset_index(drop=True)
    return processed_constraints