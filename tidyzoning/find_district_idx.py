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

    # Prepare results list
    results = []
    for _, row in joined.iterrows():
        prop_id = row['Prop_ID']
        parcel_id = row['parcel_id']
        zoning_index = row['index_right'] if not pd.isna(row['index_right']) else None
        results.append((prop_id, parcel_id, zoning_index))

    return results