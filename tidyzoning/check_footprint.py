import numpy as np
import pandas as pd
import shapely.geometry
import shapely.affinity
import rasterio
import rasterio.features
import rasterio.transform
import math
import numba
from tqdm import tqdm

# numba really does help here, 32us -> ~1us.
@numba.jit(nopython=True)
def fits(mask, width, depth):
    '''
    This function checks whether a rectangle of width x depth can fit inside the rasterized polygon described by
    mask.
    '''
    for x in range(mask.shape[0]):  # the number of the row = the depth of the mask
        for y in range(mask.shape[1]):  # the number of the column = the width of the mask
            if mask[x, y]:  # choose the raster point = True
                if ((x + width) <= mask.shape[0] and (y + depth) <= mask.shape[1]
                        and np.all(mask[x:x + width, y:y + depth])):
                    return True
                if ((x + depth) <= mask.shape[0] and (y + width) <= mask.shape[1]
                        and np.all(mask[x:x + depth, y:y + width])):
                    return True
    return False

def rect_fit(geom, dims):
    '''
    This function tests whether a rectangle of `dims` fits within the `geom`, by rasterization.
    '''
    if geom is None or geom.is_empty:
        return np.array([False for d in dims])

    w, s, e, n = rasterio.features.bounds(geom)
    # Force width/depth to exact meters
    w = math.floor(w)
    s = math.floor(s)
    n = math.ceil(n)
    e = math.ceil(e)
    assert (e - w) % 1 == 0
    assert (s - n) % 1 == 0
    width = int(round(e - w))
    depth = int(round(n - s))
    xform = rasterio.transform.from_bounds(w, s, e, n, width, depth)
    mask = rasterio.features.geometry_mask([geom], (depth, width), xform, invert=True)
    return [fits(mask, w, d) for w, d in dims]

def rot_fit(geom, dims, rotations_deg=np.arange(0, 90, 15)):
    '''
    Check if it fits for all possible rotations, 0-90 degrees. Only need to rotate through 90 degrees
    because fit() checks for fit both horizontally and vertically, and because rectangles are symmetrical.
    '''
    dims = np.array(dims)
    out = np.array([False for dim in dims])

    for rot in rotations_deg:
        if rot == 0:
            rot_geom = geom
        else:
            rot_geom = shapely.affinity.rotate(geom, rot, use_radians=False)

        out[~out] |= rect_fit(rot_geom, dims[~out])

        if np.sum(~out) == 0:
            break

    return out

def check_footprint(tidyparcel_gdf, tidybuilding):
    '''
    Function to check if buildings fit within parcels.

    Parameters:
        tidyparcel_gdf (GeoDataFrame): GeoDataFrame containing parcel geometries.
        tidybuilding (DataFrame): DataFrame containing building dimensions (width, depth).

    Returns:
        DataFrame: Results of whether buildings fit within parcels.
    '''
    results = []

    for _, parcel in tqdm(tidyparcel_gdf.iterrows(), total=len(tidyparcel_gdf), desc="Processing Parcels"):
        parcel_geom = parcel['buildable_geometry']
        if parcel_geom is None or shapely.geometry.shape(parcel_geom).is_empty:
            continue  # Skip empty parcels

        parcel_results = []
        for _, building in tidybuilding.iterrows():
            building_dims = [(building['width'], building['depth'])]
            fit_results = rot_fit(parcel_geom, building_dims)
            parcel_results.append(fit_results[0])  # Store whether the building fits

        results.append([parcel['Prop_ID'], *parcel_results])

    # Convert the results to a DataFrame
    first_column_name = tidybuilding.columns[0]
    result_columns = ['Prop_ID'] + [
        f"{int(building[first_column_name])}_{first_column_name}" for _, building in tidybuilding.iterrows()
    ]

    result_df = pd.DataFrame(results, columns=result_columns)
    return result_df