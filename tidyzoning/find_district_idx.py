def find_district_idx(tidyparcel, tidyzoning):
    """
    Find the index of the district in `tidyzoning` that contains the centroid of the `tidyparcel`.

    Parameters:
    tidyparcel (GeoDataFrame): A GeoDataFrame representing the parcel. The last row is used to find the centroid.
    tidyzoning (GeoDataFrame): A GeoDataFrame representing zoning districts with geometries.

    Returns:
    int or None: The index of the district in `tidyzoning` that contains the parcel's centroid.
                 Returns None if no unique district is found.
    """
    # Get the centroid of the last row in tidyparcel
    parcel_centroid = tidyparcel.iloc[-1].geometry.centroid
    
    # Find which tidyzoning geometries contain the centroid
    contains = tidyzoning['geometry'].apply(lambda geom: geom.contains(parcel_centroid))
    
    # Get the index of the district containing the centroid
    idx = tidyzoning[contains].index.tolist()
    
    # Return the index if unique, otherwise return None
    if len(idx) == 1:
        print(idx[0])
        return idx[0]
    else:
        print(None)
        return None
