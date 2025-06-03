import geopandas as gpd
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, MultiLineString


def read_dist(path, trans_crs="EPSG:3081", index_col="zoning_id"):
    """
    Reads a district GeoJSON (or any geospatial file), drops rows with missing geometry,
    reprojects to a given CRS, and assigns a zoning_id.

    Parameters:
    -----------
    path : str
        File path to the GeoJSON or shapefile.
    trans_crs : str, default "EPSG:3081"
        Target coordinate reference system.
    index_col : str, default "zoning_id"
        Name of the new index column for zoning ID.

    Returns:
    --------
    GeoDataFrame
        Cleaned and reprojected district layer with zoning_id column.
    """
    dist_gdf = gpd.read_file(path)
    # Valid geometry types to keep
    valid_types = (Polygon, LineString, Point, MultiPolygon, MultiLineString)
    # Apply filter to remove invalid geometries (NaN, str, None, malformed)
    dist_gdf = dist_gdf[dist_gdf.geometry.apply(lambda x: isinstance(x, valid_types) and not x.is_empty)]
    dist_gdf = dist_gdf.to_crs(trans_crs)
    dist_gdf = dist_gdf.reset_index(drop=True)
    dist_gdf[index_col] = dist_gdf.index
    return dist_gdf