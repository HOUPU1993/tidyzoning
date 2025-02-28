import os
import pandas as pd

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
    tidybuilding['fl_area'] = (unit_info['fl_area'] * unit_info['qty']).sum()
    tidybuilding['max_unit_size'] = unit_info['fl_area'].max()
    tidybuilding['min_unit_size'] = unit_info['fl_area'].min()
    tidybuilding['total_bedrooms'] = (unit_info['bedrooms'] * unit_info['qty']).sum()
    tidybuilding['total_units'] = unit_info['qty'].sum()
    tidybuilding['footprint'] = building_info['width'] * building_info['depth']
    
    # Calculate the number of units with different bedroom counts
    unique_bedrooms = unit_info["bedrooms"].unique()
    for bed in unique_bedrooms:
        tidybuilding[f'units_{bed}bed'] = unit_info.loc[unit_info["bedrooms"] == bed, "qty"].sum()
    
    # Calculate the number of units per floor
    level_qty = unit_info.groupby("level")["qty"].sum()
    for floor in [1, 2, 3]:
        tidybuilding[f'units_floor{floor}'] = level_qty.get(floor, 0)
    
    # Handle parking data (if available)
    if parking_info_file:
        parking_info = pd.read_csv(parking_info_file)
        if 'stalls' in parking_info.columns:
            for p_type in ['enclosed', 'covered', 'uncovered']:
                if (parking_info['type'] == p_type).any():
                    tidybuilding[f'parking_{p_type}'] = parking_info.loc[parking_info['type'] == p_type, 'stalls'].sum()
        
        # Calculate the number of floors for different parking types
        tidybuilding['parking_floors'] = str(parking_info.groupby('type')['level'].nunique().to_dict())
        
        # Calculate the number of garage entries for different types
        if 'entry' in parking_info.columns:
            tidybuilding['garage_entry'] = str(parking_info.groupby('type')['entry'].unique().apply(list).to_dict())
    
    return tidybuilding