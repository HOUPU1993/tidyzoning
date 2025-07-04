import json
import pandas as pd

def get_zoning_req(district_data, bldg_data=None, parcel_data=None, zoning_data=None, vars=None):
    """
    List zoning requirement values for a given building, parcel, and district.

    Parameters:
    - district_data: dict-like with a 'constraints' JSON string field
    - bldg_data, parcel_data, zoning_data: inputs for get_variables if vars not provided
    - vars: dict of precomputed variables from get_variables()

    Returns:
    - pandas.DataFrame with columns:
        constraint_name, min_value, max_value, min_val_error, max_val_error
      or a message string if no constraints.
    """
    # 1. Load constraints JSON
    district = district_data.iloc[0]
    constraints_series = district.get('constraints')
    constraints_dict = dict(constraints_series)
    if not constraints_dict or constraints_dict in ("NA",):
        return "No zoning requirements recorded for this district"

    # 2. Load variables or computer if needed
    if vars is None:
        vars = get_variables(bldg_data, parcel_data, district_data, zoning_data)
    # Ensure we have a plain dict for eval context
    vars_dict = dict(vars)

    def _process_val_list(val_list):
        """Return (value, note) for a list of constraint entries."""
        if not val_list:
            return None, None
        true_id = None
        maybe_ids = []
        note = None

        # Find the matching entry by evaluating conditions
        for idx, item in enumerate(val_list):
            conds = item.get('condition')
            # 1) Single item and no condition → select directly
            if conds is None and len(val_list) == 1:
                true_id = idx
                break
            # 2) Multiple items but no condition → add a note
            elif conds is None:
                note = "No condition field despite multiple array items"
            # 3) Single item but has a condition → also add a note
            elif len(val_list) == 1 and conds is not None:
                note = "Condition given despite a single array item"
            else:
                results = []
                for cond in conds:
                    try:
                        results.append(eval(cond, vars_dict))
                    except:
                        results.append("MAYBE")
                if all(r is True for r in results):
                    true_id = idx
                    break
                elif any(r is False for r in results):
                    continue
                else:
                    maybe_ids.append(idx)

        selected_ids = [true_id] if true_id is not None else maybe_ids
        if not selected_ids:
            return None, "No constraint conditions met"

        # Evaluate expressions for selected entries
        values = []
        for idx in selected_ids:
            expressions = val_list[idx].get('expression', [])
            for expr in expressions:
                try:
                    values.append(eval(expr, vars_dict))
                except:
                    note = "Unable to evaluate expression: incorrect format or missing variables"

        if not values:
            return None, note

        # Single vs multiple values
        if len(values) == 1:
            return values[0], note

        # Multiple: respect min_max if present
        mm = val_list[selected_ids[0]].get('min_max')
        if mm == 'min':
            return min(values), note
        elif mm == 'max':
            return max(values), note
        else:
            return (min(values), max(values)), "multiple expressions with insufficient conditions"

    # 3. Collect results
    min_values, max_values, min_notes, max_notes = [], [], [], []
    for cname, cdef in constraints_dict.items():
        min_val, min_note = _process_val_list(cdef.get('min_val', []))
        max_val, max_note = _process_val_list(cdef.get('max_val', []))

        # Round numeric values
        if isinstance(min_val, (int, float)):
            min_val = round(min_val, 4)
        if isinstance(max_val, (int, float)):
            max_val = round(max_val, 4)

        min_values.append(min_val)
        max_values.append(max_val)
        min_notes.append(min_note)
        max_notes.append(max_note)

    # 4. Build DataFrame
    df = pd.DataFrame({
        'constraint_name': list(constraints_dict.keys()),
        'min_value': min_values,
        'max_value': max_values,
        'min_val_error': min_notes,
        'max_val_error': max_notes,
    })

    return df