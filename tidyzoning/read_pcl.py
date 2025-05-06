import geopandas as gpd

def read_pcl(path, trans_crs="EPSG:3081"):
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