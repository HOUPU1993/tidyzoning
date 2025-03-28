import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union, polygonize
from shapely.validation import make_valid
from pint import UnitRegistry

def get_buildable_area(tidyparcel_with_setbacks):
    """
    Calculates the buildable area for parcels considering setbacks.

    Parameters:
    ----------
    tidyparcel_with_setbacks : GeoDataFrame with single or multiple parcels
        A GeoDataFrame containing parcel geometries along with their associated setback values and units.

    Returns:
    -------
    GeoDataFrame
        A GeoDataFrame with each parcel_id and its corresponding buildable geometry after applying setbacks.
    
    How to use:
    tidyparcel_with_setbacks = add_setbacks(tidybuilding_2_fam,  tidyzoning.loc[[2]], tidyparcel[tidyparcel['parcel_id'] == '10'])
    """
    # Initialize unit registry for unit conversion
    ureg = UnitRegistry()
    # Used to store the final results
    buildable_results = []
    
    # Iterate through each parcel_id
    for parcel_id, group in tidyparcel_with_setbacks.groupby("parcel_id"):
        group = group.copy()
        polygons = list(polygonize(group.geometry))
        parcel_geometry = unary_union(polygons)
        prop_id = group["Prop_ID"].iloc[0] if "Prop_ID" in group.columns else None
        
        # If no setback values exist, return the polygonized geometry
        if group['setback'].isna().all():
            buildable_results.append({'Prop_ID': prop_id, 'parcel_id': parcel_id, 'buildable_geometry': parcel_geometry})
            continue

        # Convert setback units to meters
        def convert_to_meters(setback, unit):
            if pd.notna(setback) and pd.notna(unit):
                try:
                    return setback * ureg(unit).to('meters').magnitude
                except:
                    return setback  # If unit conversion fails, keep original value
            return 0.0001
        
        group['setback_m'] = group.apply(lambda row: convert_to_meters(row['setback'], row['unit']), axis=1)
        # Apply buffer to each geometry based on individual setback value
        group['buffered_geometry'] = group.apply(
            lambda row: row.geometry.buffer(row.setback_m, resolution=1) if pd.notna(row.setback_m) else row.geometry,
            axis=1
        )

        # Create a union buffered polygons for each group
        unioned_geometry = unary_union(group['buffered_geometry'])
        # calculate the difference
        buildable_geom = parcel_geometry.difference(unioned_geometry)

        if not buildable_geom.is_valid:
            buildable_geom = make_valid(buildable_geom)
        if buildable_geom.is_empty:
            buildable_geom = None
        elif buildable_geom.geom_type == 'MultiPolygon':
            buildable_geom = max(buildable_geom.geoms, key=lambda g: g.area)  

        buildable_results.append({'Prop_ID': prop_id, 'parcel_id': parcel_id, 'buildable_geometry': buildable_geom})

    # transfer into geodataframe
    buildable_gdf = gpd.GeoDataFrame(buildable_results, geometry='buildable_geometry', crs='EPSG:3857').dropna(subset=['buildable_geometry'])

    return buildable_gdf
