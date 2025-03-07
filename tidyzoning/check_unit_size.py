import pandas as pd
import numpy as np
import geopandas as gpd

def check_unit_size(tidybuilding, tidyzoning):
    results = []

    # Extract units_xbed_minsize and units_xbed_maxsize from tidybuilding
    min_size_dict = {int(col.split("_")[1][0]): float(tidybuilding[col].iloc[0])
                     for col in tidybuilding.columns if col.startswith("units_") and col.endswith("_minsize")}
    
    max_size_dict = {int(col.split("_")[1][0]): float(tidybuilding[col].iloc[0])
                     for col in tidybuilding.columns if col.startswith("units_") and col.endswith("_maxsize")}

    if not min_size_dict or not max_size_dict:
        return pd.DataFrame(columns=['zoning_id', 'allowed', 'constraint_min_note', 'constraint_max_note'])

    # Iterate through tidyzoning
    for index, zoning_row in tidyzoning.iterrows():
        structure_constraints = zoning_row['structure_constraints']

        if not isinstance(structure_constraints, dict):  # Ensure it is a dictionary
            structure_constraints = {}

        # Get unit_size constraints
        unit_size_constraints = structure_constraints.get('unit_size', [])

        if not unit_size_constraints:
            results.append({'zoning_id': index, 'allowed': True, 'constraint_min_note': None, 'constraint_max_note': None})
            continue

        allowed = True  # Default to allowed
        constraint_min_note = None
        constraint_max_note = None

        # Process zoning rules
        for constraint in unit_size_constraints:
            min_val_rules = constraint.get("min_val", [])
            max_val_rules = constraint.get("max_val", [])
            min_select_info = None
            max_select_info = None

            def evaluate_constraints(size_dict, rules, comparison_func):
                """
                Handle min_val and max_val constraints.

                :param size_dict: min_size_dict or max_size_dict
                :param rules: min_val_rules or max_val_rules
                :param comparison_func: lambda expression for comparing unit sizes
                :return: (allowed status (True / False / "MAYBE"), constraint information select_info)
                """
                constraint_values = {}  # Ensure each bedroom only stores corresponding calculated values
                select_info = None

                def evaluate_expression(expression, context):
                    """ Evaluate mathematical expression, e.g., '950 + 150 * (bedrooms - 2)' """
                    try:
                        return eval(str(expression), {}, context)
                    except Exception:
                        return None  # Return None if evaluation fails

                # Method 1: Condition matching
                if isinstance(rules, list):
                    for num_bedrooms, size in size_dict.items():
                        size = float(size)  # Ensure size is float
                        for rule in rules:
                            conditions = rule.get("conditions", [])
                            expression = rule.get("expression", None)
                            rule_select_info = rule.get("select_info", None)

                            if expression is None:
                                continue  # Skip if no data

                            # Convert and evaluate expression
                            context = {"bedrooms": num_bedrooms}
                            if isinstance(expression, list):
                                evaluated_values = [evaluate_expression(expr, context) for expr in expression]
                            else:
                                evaluated_values = [evaluate_expression(expression, context)]

                            # Filter None values
                            evaluated_values = [val for val in evaluated_values if val is not None]

                            # Use eval() to parse conditions
                            try:
                                if any(eval(cond, {}, context) for cond in conditions) or not conditions:
                                    constraint_values[num_bedrooms] = evaluated_values  # Only store corresponding num_bedrooms values
                                    if rule_select_info:
                                        select_info = rule_select_info
                            except Exception:
                                continue  # Skip if parsing fails

                # Method 2: Direct expression
                elif isinstance(rules, dict) and "expression" in rules:
                    for num_bedrooms in size_dict.keys():
                        evaluated_value = evaluate_expression(rules["expression"], {"bedrooms": num_bedrooms})
                        if evaluated_value is not None:
                            constraint_values[num_bedrooms] = [evaluated_value]

                # Handle select logic
                if not constraint_values:
                    return True, select_info  # Default to allowed if no constraints

                allowed_list = []
                for num_bedrooms, values in constraint_values.items():
                    if num_bedrooms in size_dict:
                        building_size = size_dict[num_bedrooms]  # Only compare corresponding `bedrooms`
                        checks = [comparison_func(building_size, v) for v in values]

                        if "either" in rules:
                            allowed_list.append(any(checks))  # Only one condition needs to be met
                        elif "unique" in rules:
                            if all(checks):
                                allowed_list.append(True)
                            elif not any(checks):
                                allowed_list.append(False)
                            else:
                                allowed_list.append("MAYBE")
                        else:
                            allowed_list.append(all(checks))  # Default: all conditions need to be met

                if "MAYBE" in allowed_list:
                    return "MAYBE", select_info
                return all(allowed_list), select_info

            # Check minimum value
            min_allowed, min_select_info = evaluate_constraints(min_size_dict, min_val_rules, lambda x, y: x >= y)

            # Check maximum value
            max_allowed, max_select_info = evaluate_constraints(max_size_dict, max_val_rules, lambda x, y: x <= y)

            # Combine min and max results
            if min_allowed == "MAYBE" or max_allowed == "MAYBE":
                allowed = "MAYBE"
            else:
                allowed = min_allowed and max_allowed

            # Store constraint notes
            if min_select_info:
                constraint_min_note = min_select_info
            if max_select_info:
                constraint_max_note = max_select_info

        results.append({'zoning_id': index, 'allowed': allowed, 'constraint_min_note': constraint_min_note, 'constraint_max_note': constraint_max_note})

    return pd.DataFrame(results)