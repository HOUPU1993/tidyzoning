import geopandas as gpd  
import pandas as pd     

def find_district_idx(tidyparcel, tidyzoning):
    """
    Optimized version: Find the indices of the districts in `tidyzoning` that contain the centroids of the `tidyparcel`.

    Parameters:
    tidyparcel (GeoDataFrame): A GeoDataFrame representing the parcel.
                               Must include rows with 'centroid' in the 'side' column.
    tidyzoning (GeoDataFrame): A GeoDataFrame representing zoning districts with geometries.

    Returns:
    list of tuples: A list of tuples where each tuple contains:
                    Prop_ID and Pacel_id are from Tidyparcel
                    tidyzoning_index are from Tidyzoning
                    (Prop_ID, parcel_id, tidyzoning_index) if a match is found,
                    or (Prop_ID, parcel_id, None) if no match is found.
    """
    # Filter rows with centroids
    centroid_rows = tidyparcel[tidyparcel['side'] == 'centroid']
    if centroid_rows.empty:
        print("No centroids found in tidyparcel.")
        return []

    # Perform spatial join to find matches
    joined = gpd.sjoin(centroid_rows, tidyzoning, how='left', predicate='within')

    # Create the DataFrame directly with required columns
    results_df = pd.DataFrame({
        "prop_id": joined["Prop_ID"],
        "object_id": joined["parcel_id"],
        "zoning_id": joined["index_right"]
    })

    # Replace NaN zoning_id with None for consistency
    results_df["zoning_id"] = results_df["zoning_id"].where(pd.notna(results_df["zoning_id"]), None)
    results_df["zoning_id"] = results_df["zoning_id"].astype(str)

    return results_df