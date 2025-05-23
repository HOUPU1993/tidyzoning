import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union, polygonize
from shapely.validation import make_valid
from pint import UnitRegistry

def get_buildable_area(tidyparcel_with_setbacks):
    """
    Calculates the buildable area for parcels considering setbacks.
    
    This updated function supports rows where the 'setback' column may contain multiple values (e.g., [20,15]).
    For each row it extracts the minimum and maximum setback values, converts them to meters, and creates two
    buffered geometries. Then, for each parcel (grouped by parcel_id), it computes:
    
      - The relaxable region: the difference between the parcel geometry and the union of all minimum setback buffers.
      - The strict region: the difference between the parcel geometry and the union of all maximum setback buffers.
      
    Parameters:
    -----------
    tidyparcel_with_setbacks : GeoDataFrame
        A GeoDataFrame containing parcel geometries along with their associated setback values and units.
        The 'setback' column may contain a single numeric value or a list of numeric values.
    
    Returns:
    --------
    GeoDataFrame
        A GeoDataFrame with each parcel_id and its corresponding buildable geometries:
          - buildable_geometry_relaxable: Region after applying the minimum setback buffer.
          - buildable_geometry_strict: Region after applying the maximum setback buffer.
    
    How to use:
    -----------
    tidyparcel_with_setbacks = add_setbacks(tidybuilding_2_fam, tidyzoning.loc[[2]], 
                                              tidyparcel[tidyparcel['parcel_id'] == '10'])
    """
    # Initialize unit registry for unit conversion
    ureg = UnitRegistry()
    buildable_results = []
    fallback_ids = []
    
    # Function to convert a single setback value to meters
    # def convert_to_meters(value, unit):
    #     if pd.notna(value) and pd.notna(unit):
    #         try:
    #             return value * ureg(unit).to('meters').magnitude
    #         except Exception:
    #             return value  # if conversion fails, return the original value
    #     return 0.0001  # fallback small buffer value if value/unit is missing

    # Function to convert a single setback value to meters
    def convert_to_meters(value, unit):
        try:
            # Try to convert value to a floating point number to make sure it's a single scalar
            scalar_value = float(value)
        except Exception:
            return 0.0001

        if pd.notna(scalar_value) and pd.notna(unit):
            try:
                return scalar_value * ureg(unit).to('meters').magnitude
            except Exception:
                return 0.0001  # # if conversion fails, return the 0.001
        return 0.0001  # fallback small buffer value if value/unit is missing

    def flatten_vals(sb):
        """
        Flattens nested lists of setbacks into a single list of scalars.
        """
        flat = []
        if isinstance(sb, list):
            for v in sb:
                if isinstance(v, list):
                    flat.extend(v)
                else:
                    flat.append(v)
        else:
            flat.append(sb)
        return flat

    # Process each parcel (grouped by parcel_id)
    for parcel_id, group in tidyparcel_with_setbacks.groupby("parcel_id"):
        group = group.copy()
        # Combine the parcel geometries (assumed to form a contiguous parcel)
        polygons = list(polygonize(group.geometry))
        parcel_geometry = unary_union(polygons)
        prop_id = group["Prop_ID"].iloc[0] if "Prop_ID" in group.columns else None
        fallback_ids.append({'Prop_ID': prop_id, 'parcel_id': parcel_id})

        # If all setback values are missing, return the parcel geometry as both buildable areas.
        if group['setback'].isna().all():
            buildable_results.append({
                'Prop_ID': prop_id,
                'parcel_id': parcel_id,
                'buildable_geometry_relaxable': parcel_geometry,
                'buildable_geometry_strict': parcel_geometry
            })
            continue

        # For each row, determine min and max setback values (whether single value or list) and create buffers.
        def process_row(row):
            # sb = row['setback']
            # unit = row['unit']
            # # If setback is a list, extract min and max; otherwise, use the single value for both.
            # if isinstance(sb, list):
            #     min_sb = min(sb) if len(sb) > 0 else None
            #     max_sb = max(sb) if len(sb) > 0 else None
            # else:
            #     min_sb = sb
            #     max_sb = sb
            # # Convert setbacks to meters
            # min_sb_m = convert_to_meters(min_sb, unit) if min_sb is not None else 0.0001
            # max_sb_m = convert_to_meters(max_sb, unit) if max_sb is not None else 0.0001
            # # Create buffered geometries for min and max setback
            # buffered_min = row.geometry.buffer(min_sb_m, resolution=1) if pd.notna(min_sb_m) else row.geometry
            # buffered_max = row.geometry.buffer(max_sb_m, resolution=1) if pd.notna(max_sb_m) else row.geometry
            # return pd.Series({'buffered_geometry_min': buffered_min, 'buffered_geometry_max': buffered_max})
            sb_list = flatten_vals(row['setback'])
            # Determine min/max setback values
            min_sb = min(sb_list) if sb_list else 0
            max_sb = max(sb_list) if sb_list else 0
            # Convert to meters
            unit = row.get('unit')
            min_m = convert_to_meters(min_sb, unit)
            max_m = convert_to_meters(max_sb, unit)
            # Create buffers
            buffered_min = row.geometry.buffer(min_m, resolution=1)
            buffered_max = row.geometry.buffer(max_m, resolution=1)
            return pd.Series({'buffered_geometry_min': buffered_min, 'buffered_geometry_max': buffered_max})

        buffers = group.apply(process_row, axis=1)
        group = pd.concat([group, buffers], axis=1)

        # Create union of all minimum and maximum buffered geometries for the group
        unioned_buffered_min = unary_union(group['buffered_geometry_min'])
        unioned_buffered_max = unary_union(group['buffered_geometry_max'])

        # Calculate the buildable areas by subtracting the setbacks buffers from the original parcel geometry
        buildable_geom_min = parcel_geometry.difference(unioned_buffered_min)
        buildable_geom_max = parcel_geometry.difference(unioned_buffered_max)

        # Validate and fix geometries if needed
        if not buildable_geom_min.is_valid:
            buildable_geom_min = make_valid(buildable_geom_min)
        if not buildable_geom_max.is_valid:
            buildable_geom_max = make_valid(buildable_geom_max)

        if buildable_geom_min.is_empty:
            buildable_geom_min = None
        elif buildable_geom_min.geom_type == 'MultiPolygon':
            buildable_geom_min = max(buildable_geom_min.geoms, key=lambda g: g.area)

        if buildable_geom_max.is_empty:
            buildable_geom_max = None
        elif buildable_geom_max.geom_type == 'MultiPolygon':
            buildable_geom_max = max(buildable_geom_max.geoms, key=lambda g: g.area)

        # Case for some mistakes
        if buildable_geom_min is None and buildable_geom_max is not None:
            buildable_geom_min = buildable_geom_max
        elif buildable_geom_max is None and buildable_geom_min is not None:
            buildable_geom_max = buildable_geom_min
        elif buildable_geom_min is None and buildable_geom_max is None:
            try:
                fallback_polygon = parcel_geometry
                if fallback_polygon is None or fallback_polygon.is_empty:
                    raise ValueError("Fallback polygon invalid")
                buildable_geom_min = fallback_polygon
                buildable_geom_max = fallback_polygon
            except Exception:
                buildable_geom_min = "error"
                buildable_geom_max = "error"

        buildable_results.append({
            'Prop_ID': prop_id,
            'parcel_id': parcel_id,
            'buildable_geometry_relaxable': buildable_geom_min,
            'buildable_geometry_strict': buildable_geom_max
        })


    # # Note: one of the geometries is set as the active geometry, while the other is stored as an attribute.
    # buildable_gdf = gpd.GeoDataFrame(buildable_results, geometry='buildable_geometry_strict', crs='EPSG:3081')
    # buildable_gdf = buildable_gdf.dropna(subset=['buildable_geometry_relaxable', 'buildable_geometry_strict'])

    # return buildable_gdf

    # Convert results into a GeoDataFrame.
    buildable_df = pd.DataFrame(buildable_results)
    required_columns = ['buildable_geometry_relaxable', 'buildable_geometry_strict']
    # If buildable_df is empty or missing the required key columns, use the previously saved fallback_ids to construct the return result
    if buildable_df.empty or not all(col in buildable_df.columns for col in required_columns):
        fallback_df = pd.DataFrame(fallback_ids)  # fallback_ids has already recorded each parcel's Prop_ID and parcel_id in the for loop
        fallback_df['buildable_geometry_relaxable'] = None
        fallback_df['buildable_geometry_strict'] = None
        return gpd.GeoDataFrame(fallback_df, geometry='buildable_geometry_strict', crs='EPSG:3081')
    else:
        return gpd.GeoDataFrame(buildable_df, geometry='buildable_geometry_strict', crs='EPSG:3081')
