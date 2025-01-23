import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union, polygonize

def get_zoning_req(tidybuilding, tidyzoning, tidyparcel=None):
    """
    Process building, zoning, and parcel information to generate structured Zoning requirement data.
    
    :param tidybuilding: Building data (DataFrame)
    :param tidyzoning: Zoning data (DataFrame)
    :param tidyparcel: Parcel data (GeoDataFrame), optional
    :return: DataFrame containing all calculated results
    """
    # extract info from the district constraints
    def zoning_extract(tidybuilding, tidyzoning, tidyparcel=None):
        columns_to_extract = ['structure_constraints', 'other_constraints', 'lot_constraints']
        extracted_data = []
        
        for col in columns_to_extract:
            for index, row in tidyzoning.iterrows():
                constraints = row[col]
                if isinstance(constraints, dict): # if the constraints are dictionaries
                    for constraint_type, entries in constraints.items():
                        if isinstance(entries, list):  # Iterate over the list of keys and values
                            for entry in entries:
                                flattened_entry = {
                                    "original_index": index,
                                    "source_column": col,
                                    "constraint_type": constraint_type,
                                }
                                for key, value in entry.items(): # Save all key-value pairs in the entry
                                    flattened_entry[key] = value
                                extracted_data.append(flattened_entry) # Add results to the list
        # transfer district info into the dataframe
        district_constraints = pd.DataFrame(extracted_data)

        if tidyparcel is None: # check whether tidyparcel exist or not
            lot_width, lot_depth, lot_area = None, None, None
        else:
            results = []
            for prop_id, group in tidyparcel.groupby('Prop_ID'):
                front_of_parcel = group[group['side'] == "front"]
                side_of_parcel = group[group['side'] == "Interior side"]
                parcel_without_centroid = group[(group['side'].notna()) & (group['side'] != "centroid")]
                # calculate the width and depth
                lot_width = front_of_parcel.geometry.length.sum() * 3.28084
                lot_depth = side_of_parcel.geometry.length.sum() * 3.28084
                # calculate the area for each parcel
                polygons = polygonize(unary_union(parcel_without_centroid.geometry))
                lot_polygon = unary_union(polygons)
                lot_area = lot_polygon.area * 10.7639
                results.append({
                    "Prop_ID": prop_id,
                    "lot_width": lot_width,
                    "lot_depth": lot_depth,
                    "lot_area": lot_area
                })
            # transfer parcel info into dataframe
            parcel_results = pd.DataFrame(results)
            lot_width = parcel_results["lot_width"].iloc[0] if not parcel_results.empty else None
            lot_depth = parcel_results["lot_depth"].iloc[0] if not parcel_results.empty else None
            lot_area = parcel_results["lot_area"].iloc[0] if not parcel_results.empty else None

        # check the data from the tidybuilding
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
        fl_area = tidybuilding.get('floor_area', [None])[0]
        parking_open = tidybuilding.get('parking_open', [None])[0]
        parking_enclosed = tidybuilding.get('parking_enclosed', [None])[0]
        parking = tidybuilding.get('parking', [None])[0]
        height = tidybuilding.get('building_height', [None])[0]
        floors = tidybuilding.get('total_floors', [None])[0]
        min_unit_size = tidybuilding.get('min_unit_size', [None])[0]
        max_unit_size = tidybuilding.get('max_unit_size', [None])[0]
        far = fl_area / lot_area if lot_area is not None else None

        # summarize the resul
        return {
            # from tidyzoning
            "district_constraints": district_constraints, 
            # from tidyparcel
            "lot_width": lot_width, 
            "lot_depth": lot_depth,
            "lot_area": lot_area,
            # from tidybuilding
            "bedrooms": bedrooms, 
            "units_0bed": units_0bed,
            "units_1bed": units_1bed,
            "units_2bed": units_2bed,
            "units_3bed": units_3bed,
            "units_4bed": units_4bed,
            "total_units": total_units,
            "fl_area": fl_area,
            "parking_open": parking_open,
            "parking_enclosed": parking_enclosed,
            "parking": parking,
            "height": height,
            "floors": floors,
            "min_unit_size": min_unit_size,
            "max_unit_size": max_unit_size,
            # combined tidy zoning and tidyparcel together
            "far": far   
        }

    def extract_expression(value):
        return value.get("expression") if isinstance(value, dict) and "expression" in value else value

    result = zoning_extract(tidybuilding, tidyzoning, tidyparcel)
    result["district_constraints"]["min_val"] = result["district_constraints"]["min_val"].apply(extract_expression)
    result["district_constraints"]["max_val"] = result["district_constraints"]["max_val"].apply(extract_expression)

    # process zoning constraints base on the type of building
    def process_zoning_constraints(result, tidybuilding):
        # extract the info from constraints
        district_constraints = result["district_constraints"]
        bldg_type = find_bldg_type(tidybuilding)
        # Initialize results list and warning count
        results = []
        warnings = 0

        # Iterate through each constraint
        for _, constraint in district_constraints.iterrows():
            use_name = constraint["use_name"]
            min_val_expression = constraint["min_val"]
            max_val_expression = constraint["max_val"]
            constraint_min_val = None
            constraint_max_val = None

            # check the bldg type
            if bldg_type not in use_name:
                # print(f"Skipping constraint '{constraint['constraint_type']}': because building type '{bldg_type}' does not match use name '{use_name}'.")
                continue

            def evaluate_conditions_and_expressions(rules, context):
                warnings = 0

                for rule in rules:
                    logical_operator = rule.get('logical_operator').upper()
                    conditions = rule.get('conditions', [])
                    expression = rule.get('expression', None) # get the simple expression
                    expressions_list = rule.get('expression', [])  # get the list of expression
                    select = rule.get('select', None)

                    # Parse conditions
                    try:
                        if logical_operator == 'AND':
                            conditions_value = all(eval(cond, {}, context) for cond in conditions)
                        elif logical_operator == 'OR':
                            conditions_value = any(eval(cond, {}, context) for cond in conditions)
                        else:
                            conditions_value = False
                    except Exception as e:
                        warnings += 1
                        print(f"Warning: Failed to evaluate conditions: {conditions}. Error: {e}")
                        continue

                    if conditions_value:
                        try:
                            # If it's a single expression
                            if expression:
                                return eval(expression, {}, context)
                            # If it's multiple expressions, handle with select
                            if expressions_list:
                                evaluated_expressions = [eval(expr, {}, context) for expr in expressions_list]
                                if select == 'min':
                                    return min(evaluated_expressions)
                                elif select == 'max':
                                    return max(evaluated_expressions)
                                elif select is None:
                                    return evaluated_expressions  # 默认返回所有表达式的值
                        except Exception as e:
                            warnings += 1
                            print(f"Warning: Failed to evaluate expressions: {expression or expressions_list}. Error: {e}")
                            continue

                return None  # If no rule satisfies the condition, return None

            # Use the complete context (all key-value pairs in result)
            context = {**result}
            # print(f"Context before evaluation: {context}")

            # deal with min_val
            if isinstance(min_val_expression, str): # If it's specifc value
                try:
                    constraint_min_val = eval(min_val_expression, {}, context)
                except Exception as e:
                    warnings += 1
            elif isinstance(min_val_expression, list):  # If it's a complex rule
                constraint_min_val = evaluate_conditions_and_expressions(min_val_expression, context)

            # deal with max_val
            if isinstance(max_val_expression, str): # If it's specifc value
                try:
                    constraint_max_val = eval(max_val_expression, {}, context)
                except Exception as e:
                    warnings += 1
            elif isinstance(max_val_expression, list): # If it's a complex rule
                constraint_max_val = evaluate_conditions_and_expressions(max_val_expression, context)

            # saving results
            results.append({
                "constraint_type": constraint["source_column"],
                "spec_type": constraint["constraint_type"],
                "min_value": constraint_min_val,
                "max_value": constraint_max_val,
                "unit": constraint["unit"]
            })

        # print warnings
        if warnings > 0:
            print(f"Completed with {warnings} warnings.")

        # transfer final result into DataFrame
        return pd.DataFrame(results)

    processed_constraints = process_zoning_constraints(result, tidybuilding)
    return processed_constraints