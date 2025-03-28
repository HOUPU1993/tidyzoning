import os
import pandas as pd

'''how to use: 
file_path = r"C:\Users\Admin\Desktop\New folder (6)\tidybuilding\4_fam_wide/"
tidybuilding_4_fam = unify_tidybuilding(file_path)
'''


def unify_tidybuilding(file_path):
    # Ensure file_path ends with the correct separator
    file_path = file_path.rstrip("/\\") + os.sep
    
    # Find files
    bldg_info_file = None
    unit_info_file = None
    parking_info_file = None
    
    for file in os.listdir(file_path):
        if file.endswith("bldg_info.csv"):
            bldg_info_file = file_path + file
        elif "unit_info.csv" in file:
            unit_info_file = file_path + file
        elif "parking_info.csv" in file:
            parking_info_file = file_path + file
    
    if not bldg_info_file or not unit_info_file:
        raise FileNotFoundError("Missing required bldg_info.csv or unit_info.csv file.")
    
    # Read files
    building_info = pd.read_csv(bldg_info_file)
    unit_info = pd.read_csv(unit_info_file)
    
    # Create tidybuilding DataFrame
    tidybuilding = building_info.copy()
    
    # Calculate floor area and unit information
    tidybuilding['net_fl_area'] = (unit_info['fl_area'] * unit_info['qty']).sum()
    tidybuilding['max_unit_size'] = unit_info['fl_area'].max()
    tidybuilding['min_unit_size'] = unit_info['fl_area'].min()
    tidybuilding['mean_unit_size'] = unit_info['fl_area'].min()
    tidybuilding['total_bedrooms'] = (unit_info['bedrooms'] * unit_info['qty']).sum()
    tidybuilding['total_units'] = unit_info['qty'].sum()
    tidybuilding['footprint'] = building_info['width'] * building_info['depth']
    
    # Calculate the number of units with different bedroom counts
    unique_bedrooms = unit_info["bedrooms"].unique()
    for bed in unique_bedrooms:
        if bed < 4:
            tidybuilding[f'units_{bed}bed'] = unit_info.loc[unit_info["bedrooms"] == bed, "qty"].sum()
        else:
            tidybuilding["units_4bed"] = tidybuilding.get("units_4bed", 0) + unit_info.loc[unit_info["bedrooms"] == bed, "qty"].sum()
            
    # Calculate unique bedrooms and their corresponding unit sizes
    for bed in unique_bedrooms:
        tidybuilding[f'units_{bed}bed_minsize'] = unit_info.loc[unit_info["bedrooms"] == bed, "fl_area"].min()

    # Calculate unique bedrooms and their corresponding unit sizes
    for bed in unique_bedrooms:
        tidybuilding[f'units_{bed}bed_maxsize'] = unit_info.loc[unit_info["bedrooms"] == bed, "fl_area"].max()

    # Calculate the number of units per floor
    level_qty = unit_info.groupby("level")["qty"].sum()
    for floor in [1, 2, 3]:
        tidybuilding[f'units_floor{floor}'] = level_qty.get(floor, 0)

    # Read parking_info data
    if parking_info_file:
        parking_info = pd.read_csv(parking_info_file)

        # Calculate parking types
        parking_covered = parking_info.loc[parking_info['type'] == 'covered', 'stalls'].sum()
        parking_uncovered = parking_info.loc[parking_info['type'] == 'uncovered', 'stalls'].sum()
        parking_enclosed = parking_info.loc[parking_info['type'] == 'enclosed', 'stalls'].sum()
        # Calculate number of floors with parking
        parking_floors = len(parking_info['level'].dropna().unique()) if not parking_info['level'].isna().all() else 0
        # Check for underground parking
        parking_bel_grade = "yes" if (parking_info['level'].dropna() < 0).any() else "no"
        # Get garage entry locations
        valid_entries = parking_info['entry'].dropna().unique()
        garage_entry = valid_entries if len(valid_entries) > 0 else np.nan
        # add specific column to store the value
        tidybuilding["parking_covered"] = parking_covered
        tidybuilding["parking_uncovered"] = parking_uncovered
        tidybuilding["parking_enclosed"] = parking_enclosed
        tidybuilding["parking_floors"] = parking_floors
        tidybuilding["parking_bel_grade"] = parking_bel_grade
        tidybuilding["garage_entry"] = [garage_entry]

    return tidybuilding