import json
import pandas as pd

def unify_tidybuilding(bldg_data_file=None, ozfs_data_file=None, bldg_data_string=None):
    """
    Get summarized building info in one DataFrame row.

    Parameters:
    -----------
    bldg_data_file : str or None
        Path to a JSON file containing building attributes.
    ozfs_data_file : str or None
        Path to a JSON file containing ozfs definitions (e.g., height rules).
    bldg_data_string : str or None
        A JSON-formatted string containing building attributes.

    Returns:
    --------
    pd.DataFrame or None
        A single-row DataFrame with building summary information.
        If all inputs are None, prints a message and returns None.
    """
    # If all three inputs are None, print a message and exit
    if bldg_data_file is None and ozfs_data_file is None and bldg_data_string is None:
        print("No input given \nPlease provide either a JSON file path or JSON bldg_data_string")
        return

    # Prefer bldg_data_string; otherwise, try to read from bldg_data_file
    if bldg_data_string is not None:
        try:
            listed_json = json.loads(bldg_data_string)
        except json.JSONDecodeError:
            raise ValueError("The bldg_data_string must be in JSON format")
    elif bldg_data_file is not None:
        try:
            with open(bldg_data_file, 'r', encoding='utf-8') as f:
                listed_json = json.load(f)
        except Exception:
            raise ValueError("The .bldg file must be in JSON format")
    else:
        listed_json = None  # If only ozfs_data_file is provided, listed_json will be None

    # Check that JSON contains required sections
    if listed_json is None or not all(k in listed_json for k in ("bldg_info", "unit_info", "level_info")):
        raise ValueError("Improper format: JSON must contain bldg_info, unit_info, and level_info sections")

    # Extract fl_area, bedrooms, qty from unit_info
    fl_area_list = []
    bedrooms_list = []
    qty_list = []
    for unit in listed_json["unit_info"]:
        fl_area_list.append(unit.get("fl_area"))
        bedrooms_list.append(unit.get("bedrooms"))
        qty_list.append(unit.get("qty"))
    unit_info_df = pd.DataFrame({
        "fl_area": fl_area_list,      # unit floor area
        "bedrooms": bedrooms_list,    # number of bedrooms
        "qty": qty_list               # quantity of that unit type
    })

    # Extract level and gross_fl_area from level_info
    level_list = []
    gross_fl_area_list = []
    for lev in listed_json["level_info"]:
        level_list.append(lev.get("level"))
        gross_fl_area_list.append(lev.get("gross_fl_area"))
    level_info_df = pd.DataFrame({
        "level": level_list,               # floor number
        "gross_fl_area": gross_fl_area_list  # gross floor area per level
    })

    # Extract basic properties from bldg_info
    bldg_info = listed_json["bldg_info"]
    height_top = bldg_info.get("height_top")
    width = bldg_info.get("width")
    depth = bldg_info.get("depth")
    # Default roof_type to "flat" if not provided
    roof_type = bldg_info.get("roof_type", "flat")
    # Default parking to 0 if not provided
    parking = bldg_info.get("parking", 0)
    # Default height_eave to height_top if not provided
    height_eave = bldg_info.get("height_eave", height_top)
    # Default height_deck to height_top if not provided
    height_deck = bldg_info.get("height_deck", height_top)

    # Calculate stories (number of floors)
    stories = int(level_info_df["level"].max())
    # Calculate total_units (sum of qty)
    total_units = int(unit_info_df["qty"].sum())
    # Determine building type: "4_plus" if more than 3 units, else "<n>_unit"
    bldg_type = "4_plus" if total_units > 3 else f"{total_units}_unit"
    # Calculate gross building floor area (sum of all levels)
    gross_fl_area_sum = float(level_info_df["gross_fl_area"].sum())
    # Calculate total bedrooms (bedrooms * qty, summed)
    total_bedrooms = int((unit_info_df["bedrooms"] * unit_info_df["qty"]).sum())
    # Floor area of first and top levels
    fl_area_first = float(level_info_df.loc[
        level_info_df["level"] == level_info_df["level"].min(), "gross_fl_area"
    ].iloc[0])
    fl_area_top = float(level_info_df.loc[
        level_info_df["level"] == level_info_df["level"].max(), "gross_fl_area"
    ].iloc[0])
    # Count units by bedroom categories
    units_0bed = int(unit_info_df.loc[unit_info_df["bedrooms"] == 0, "qty"].sum())
    units_1bed = int(unit_info_df.loc[unit_info_df["bedrooms"] == 1, "qty"].sum())
    units_2bed = int(unit_info_df.loc[unit_info_df["bedrooms"] == 2, "qty"].sum())
    units_3bed = int(unit_info_df.loc[unit_info_df["bedrooms"] == 3, "qty"].sum())
    # Bedrooms > 3 counted as "4bed+"
    units_4bed = int(unit_info_df.loc[unit_info_df["bedrooms"] > 3, "qty"].sum())
    # Overall min and max unit sizes (across all units)
    min_unit_size = float(unit_info_df["fl_area"].min())
    max_unit_size = float(unit_info_df["fl_area"].max())

    # Get unique bedroom counts from unit_info_df
    unique_bedrooms = unit_info_df["bedrooms"].unique()
    # For each bedroom count, compute the minimum fl_area
    bedroom_mins = {}
    for bed in unique_bedrooms:
        min_size = unit_info_df.loc[unit_info_df["bedrooms"] == bed, "fl_area"].min()
        bedroom_mins[f'units_{bed}bed_minsize'] = float(min_size)
    # For each bedroom count, compute the maximum fl_area
    bedroom_maxs = {}
    for bed in unique_bedrooms:
        max_size = unit_info_df.loc[unit_info_df["bedrooms"] == bed, "fl_area"].max()
        bedroom_maxs[f'units_{bed}bed_maxsize'] = float(max_size)

    # Build a dictionary with all extracted properties, to be converted into a single-row DataFrame
    bldg_summary = {
        "height_top": height_top,           # building top height
        "width": width,                     # building width
        "depth": depth,                     # building depth
        "roof_type": roof_type,             # roof type
        "parking": parking,                 # parking (count or flag)
        "height_eave": height_eave,         # eave height
        "height_deck": height_deck,         # deck height
        "stories": stories,                 # number of stories
        "total_units": total_units,         # total number of units
        "type": bldg_type,                  # building type classification
        "gross_fl_area": gross_fl_area_sum, # total gross floor area
        "total_bedrooms": total_bedrooms,   # total number of bedrooms
        "fl_area_first": fl_area_first,     # first-floor area
        "fl_area_top": fl_area_top,         # top-floor area
        "units_0bed": units_0bed,           # number of 0-bedroom units
        "units_1bed": units_1bed,           # number of 1-bedroom units
        "units_2bed": units_2bed,           # number of 2-bedroom units
        "units_3bed": units_3bed,           # number of 3-bedroom units
        "units_4bed": units_4bed,           # number of 4+ bedroom units
        "min_unit_size": min_unit_size,     # overall minimum unit size
        "max_unit_size": max_unit_size      # overall maximum unit size
    }

    # Merge the per-bedroom-size min/max values into the summary
    bldg_summary.update(bedroom_mins)
    bldg_summary.update(bedroom_maxs)

    # If ozfs_data_file is provided, read definitions to compute “height” (matching roof_type)
    if ozfs_data_file is not None:
        try:
            with open(ozfs_data_file, 'r', encoding='utf-8') as f:
                listed_ozfs = json.load(f)
        except Exception:
            # If ozfs file cannot be parsed, default height to height_top
            bldg_summary["height"] = height_top
        else:
            # Check if definitions.height exists
            height_value = height_top  # default
            if "definitions" in listed_ozfs and "height" in listed_ozfs["definitions"]:
                for definition in listed_ozfs["definitions"]["height"]:
                    # If roof_type matches, eval the expression
                    if definition.get("roof_type") == roof_type and "expression" in definition:
                        try:
                            height_value = eval(definition["expression"])
                        except Exception:
                            height_value = height_top
                        break
            bldg_summary["height"] = height_value
    else:
        # If no ozfs_data_file, set height = height_top
        bldg_summary["height"] = height_top

    # Convert the dictionary into a single-row DataFrame
    bldg_info_df = pd.DataFrame([bldg_summary])

    return bldg_info_df