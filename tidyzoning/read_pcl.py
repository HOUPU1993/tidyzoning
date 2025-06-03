import geopandas as gpd
from tidyzoning import find_district_idx

def read_pcl(path, dist, trans_crs="EPSG:3081"):
    """
    Reads a parcel GeoJSON (or any geospatial file) and reprojects it to a specified coordinate reference system (CRS).

    Parameters:
    -----------
    path : str
        File path to the GeoJSON or shapefile.
    trans_crs : str, default "EPSG:3081"
        Target coordinate reference system.

    Returns:
    --------
    GeoDataFrame
        Cleaned and reprojected district layer with zoning_id column.
    """
    parcel_gdf = gpd.read_file(path)
    parcel_gdf = parcel_gdf.to_crs(trans_crs)
    return parcel_gdf





# import geopandas as gpd
# from tidyzoning import find_district_idx

# def read_pcl(path, dist, trans_crs="EPSG:3081"):
#     """
#     Reads a parcel GeoJSON (or any geospatial file) and reprojects it to a specified coordinate reference system (CRS).

#     Parameters:
#     -----------
#     path : str
#         File path to the GeoJSON or shapefile.
#     trans_crs : str, default "EPSG:3081"
#         Target coordinate reference system.

#     Returns:
#     --------
#     GeoDataFrame
#         Cleaned and reprojected district layer with zoning_id column.
#     """
#     parcel_gdf = gpd.read_file(path)
#     parcel_gdf = parcel_gdf.to_crs(trans_crs)
#     find_district_idx_results = find_district_idx(parcel_gdf, dist)
#     parcel_gdf = parcel_gdf.merge(find_district_idx_results, left_index=True, right_index=True, how='left')
#     parcel_gdf = parcel_gdf.rename(columns={'parcel_id_x': 'parcel_id'})
#     parcel_gdf = parcel_gdf.drop(columns=['parcel_id_y'])
#     parcel_gdf['zoning_id'] = parcel_gdf['zoning_id'].astype(int)
#     return parcel_gdf