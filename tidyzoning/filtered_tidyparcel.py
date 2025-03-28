import geopandas as gpd
from shapely.geometry import MultiPolygon

def filtered_tidyparcel(tidyparcel_fp, tidyzoning_gdf, output_fp=None):
    """
    Filters tidyparcel GeoDataFrame by checking if centroids fall within the zoning union.
    
    Parameters:
    - tidyparcel_fp (str): File path to the tidyparcel GeoJSON or shapefile.
    - tidyzoning_gdf (GeoDataFrame): A tidyzoning GeoDataFrame.
    - output_fp (str, optional): File path to save the filtered tidyparcel GeoDataFrame. If None, doesn't save.
    
    Returns:
    - GeoDataFrame: Filtered tidyparcel GeoDataFrame.
    """
    
    # Read and set CRS
    tidyparcel = gpd.read_file(tidyparcel_fp)
    tidyparcel = tidyparcel.set_crs(3857, allow_override=True)

    # Create union of zoning geometries
    tidyzoning_union = tidyzoning_gdf.dissolve().unary_union
    tidyzoning_union = gpd.GeoDataFrame(geometry=[tidyzoning_union], crs=tidyzoning_gdf.crs)

    # Filter centroids and spatial join
    centroids = tidyparcel[tidyparcel['side'] == 'centroid']
    centroids_with_zoning = gpd.sjoin(centroids, tidyzoning_union, how='inner', predicate='within')

    # Get valid ids
    valid_ids = centroids_with_zoning[['Prop_ID', 'parcel_id']].drop_duplicates()

    # Filter tidyparcel using valid ids
    filtered = tidyparcel.merge(valid_ids, on=['Prop_ID', 'parcel_id'], how='inner')

    # Optionally save to file
    if output_fp:
        filtered.to_file(output_fp, driver='GeoJSON')

    return filtered